import os
import time
import json
import base64
import subprocess
from pathlib import Path
from typing import Any
from pysui.abstracts import SignatureScheme
from pydantic import BaseModel
from pysui import SuiConfig, SyncClient
from pysui.sui.sui_builders.get_builders import GetChainID
from pysui.sui.sui_types.address import SuiAddress
from .config import Settings
from .exceptions import SuiCTFSandboxError
from .init import check_solve_conditions, initialize_challenge
from .utils import read_json, write_json

class ConnectionInfo(BaseModel):
    rpc_url: str
    player_address: str
    player_mnemonic: str
    artifacts: dict[str, Any]

class ChallengeService:
    def __init__(self, config: Settings | None = None):
        self.config = config or Settings()
        self.sui_process: subprocess.Popen | None = None
        self.sui_log_file = None

    def sui_cli(self, *args: str, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        command = ["sui", *args]
        return subprocess.run(
            command,
            check=check,
            text=True,
            stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
            stderr=subprocess.PIPE if capture else subprocess.DEVNULL,
        )

    def wait_for_rpc(self) -> str:
        last_error = None
        for _ in range(120):
            try:
                result = self.client().execute(GetChainID())
                if result.is_ok():
                    return result.result_data
                last_error = result.result_string
            except Exception as exc:
                last_error = exc
            time.sleep(1)
        raise SuiCTFSandboxError("rpc did not become ready", {"cause": str(last_error)})

    def switch_local_env(self) -> None:
        self.sui_cli(
            "client",
            "--client.config",
            str(self.config.client_config),
            "new-env",
            "--alias",
            "localrpc",
            "--rpc",
            self.config.rpc_url,
            check=False,
        )
        self.sui_cli(
            "client",
            "--client.config",
            str(self.config.client_config),
            "switch",
            "--env",
            "localrpc",
        )

    def configure_client(self) -> str:
        self.switch_local_env()
        deployer_address = SuiConfig.pysui_config(str(self.config.state_dir)).active_address
        return str(deployer_address)

    def sync_default_client_config(self) -> None:
        default_dir = Path.home() / ".sui" / "sui_config"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_client_config = default_dir / "client.yaml"
        default_client_config.unlink(missing_ok=True)
        default_client_config.symlink_to(self.config.client_config)

    def start_sui(self) -> None:
        config = self.config
        config.ready_file.unlink(missing_ok=True)
        config.state_dir.mkdir(parents=True, exist_ok=True)
        config.node_log.parent.mkdir(parents=True, exist_ok=True)

        if not (config.state_dir / "network.yaml").exists():
            print("[server] creating local Sui genesis")
            self.sui_cli("genesis", "-f", "--working-dir", str(config.state_dir))

        print(f"[server] starting local Sui RPC on {config.rpc_url}")
        self.sui_log_file = config.node_log.open("ab")
        self.sui_process = subprocess.Popen(
            [
                "sui",
                "start",
                "--network.config",
                str(config.state_dir),
                "--fullnode-rpc-port",
                str(config.rpc_port),
            ],
            stdout=self.sui_log_file,
            stderr=subprocess.STDOUT,
        )
        self.wait_for_rpc()
        self.configure_client()
        self.sync_default_client_config()
        config.ready_file.write_text("", encoding="utf8")
        print("[server] local Sui ready")

    def stop_sui(self) -> None:
        self.config.ready_file.unlink(missing_ok=True)
        if self.sui_process and self.sui_process.poll() is None:
            self.sui_process.terminate()
            try:
                self.sui_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.sui_process.kill()
        if self.sui_log_file:
            self.sui_log_file.close()
            self.sui_log_file = None

    def client(self, address: str | None = None) -> SyncClient:
        cfg = SuiConfig.pysui_config(str(self.config.state_dir))
        if address:
            cfg.set_active_address(SuiAddress(address))
        return SyncClient(cfg)

    def generate_player(self) -> tuple[str, str]:
        alias = f"player-{int(time.time() * 1000)}"
        mnemonic, address = SuiConfig.pysui_config(
            str(self.config.state_dir)
        ).create_new_keypair_and_address(
            scheme=SignatureScheme.ED25519,
            alias=alias,
        )
        return str(address), mnemonic

    def compile_package(self) -> dict[str, Any]:
        env = {
            **os.environ,
            "SUI_CLIENT_CONFIG": str(self.config.client_config),
        }
        result = subprocess.run(
            [
                "sui",
                "move",
                "build",
                "--dump-bytecode-as-base64",
                "--build-env",
                "testnet",
                "--path",
                str(self.config.challenge_dir),
            ],
            check=False,
            text=True,
            capture_output=True,
            env=env,
            stdin=subprocess.DEVNULL,
        )
        if result.returncode != 0:
            raise SuiCTFSandboxError(
                "package compilation failed",
                {"stdout": result.stdout, "stderr": result.stderr},
            )
        stdout = result.stdout.strip()
        payload = next((line for line in reversed(stdout.splitlines()) if line.lstrip().startswith("{")), stdout)
        compiled = json.loads(payload)
        compiled["modules"] = [list(base64.b64decode(module)) for module in compiled["modules"]]
        return compiled

    def object_changes_by_type(self, txr, kind: str, suffix: str | None = None) -> list[str]:
        matches = []
        for change in txr.object_changes or []:
            if change.get("type") != kind:
                continue
            if kind == "published":
                matches.append(change["packageId"])
            elif suffix is None or change.get("objectType", "").endswith(suffix):
                matches.append(change["objectId"])
        return matches

    def latest_instance(self) -> dict:
        instances = read_json(self.config.instances_json, [])
        if not instances:
            raise SuiCTFSandboxError("create an instance first")
        return instances[-1]

    def current_connection_info(self) -> ConnectionInfo:
        try:
            instance = self.latest_instance().copy()
            instance.pop("state", None)
            return ConnectionInfo.model_validate(instance)
        except SuiCTFSandboxError as e:
            return {"error": str(e)}

    def create_instance(self) -> ConnectionInfo:
        instances = read_json(self.config.instances_json, [])
        if instances:
            instance = instances[-1].copy()
            instance.pop("state", None)
            return ConnectionInfo.model_validate(instance)

        deployer = self.configure_client()
        player_address, player_mnemonic = self.generate_player()
        deployment = initialize_challenge(self, deployer, player_address)
        artifacts = deployment.artifacts or {}
        state = deployment.state or {}

        instance = ConnectionInfo(
            rpc_url=self.config.public_rpc_url,
            player_address=player_address,
            player_mnemonic=player_mnemonic,
            artifacts=artifacts,
        )
        stored_instance = instance.model_dump() | {"state": state}
        instances.append(stored_instance)
        write_json(self.config.instances_json, instances)
        write_json(
            self.config.deployment_json,
            {
                "rpc_url": self.config.public_rpc_url,
                "player_address": player_address,
                **artifacts,
            },
        )
        return instance

    def check_flag(self) -> dict:
        try:
            result = check_solve_conditions(self, self.latest_instance())
        except SuiCTFSandboxError as e:
            return {"error": str(e)}
        return result
