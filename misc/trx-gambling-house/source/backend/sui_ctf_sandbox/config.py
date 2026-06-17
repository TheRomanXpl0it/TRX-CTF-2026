import os
from decimal import Decimal
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

MIST_PER_SUI = Decimal("1000000000")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    state_dir: Path = Path(os.getenv("STATE_DIR", "/state"))
    contracts_dir: Path = Path(os.getenv("CONTRACTS_DIR", "/app/contracts"))
    node_log: Path = Path(os.getenv("NODE_LOG", "/state/sui.log"))
    rpc_port: int = int(os.getenv("RPC_PORT", 9000))
    launcher_port: int = int(os.getenv("LAUNCHER_PORT", 1337))
    instance_domain: str = os.getenv("INSTANCE_DOMAIN", "127.0.0.1")
    deployer_starting_balance_sui: Decimal = Decimal(os.getenv("DEPLOYER_STARTING_BALANCE_SUI", "20000000"))
    player_starting_balance_sui: Decimal = Decimal(os.getenv("PLAYER_STARTING_BALANCE_SUI", "150"))
    target_balance_sui: Decimal = Decimal(os.getenv("TARGET_BAL_SUI", "2000"))
    flag: str = os.getenv("FLAG", "TRX{fake_flag}")

    @staticmethod
    def to_mist(amount: Decimal) -> int:
        return int(amount * MIST_PER_SUI)

    @property
    def host(self) -> str:
        return self.instance_domain

    @property
    def deployer_starting_balance(self) -> int:
        return self.to_mist(self.deployer_starting_balance_sui)

    @property
    def player_starting_balance(self) -> int:
        return self.to_mist(self.player_starting_balance_sui)

    @property
    def target_balance(self) -> int:
        return self.to_mist(self.target_balance_sui)

    @property
    def challenge_dir(self) -> Path:
        if (self.contracts_dir / "Move.toml").exists():
            return self.contracts_dir
        for path in self.contracts_dir.iterdir():
            if path.is_dir() and (path / "Move.toml").exists():
                return path
        return self.contracts_dir

    @property
    def client_config(self) -> Path:
        return self.state_dir / "client.yaml"

    @property
    def keystore(self) -> Path:
        return self.state_dir / "sui.keystore"

    @property
    def deployment_json(self) -> Path:
        return self.state_dir / "deployment.json"

    @property
    def instances_json(self) -> Path:
        return self.state_dir / "instances.json"

    @property
    def ready_file(self) -> Path:
        return self.state_dir / ".ready"

    @property
    def rpc_url(self) -> str:
        return f"http://{self.host}:{self.rpc_port}"

    @property
    def public_rpc_url(self) -> str:
        return self.rpc_url
