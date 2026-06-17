import os
from typing import Any
from pydantic import BaseModel
from pysui.sui.sui_bcs import bcs
from pysui.sui.sui_txn.sync_transaction import SuiTransaction
from pysui.sui.sui_types.address import SuiAddress
from pysui.sui.sui_types.scalars import ObjectID
from .exceptions import SuiCTFSandboxError

class ChallengeInitResult(BaseModel):
    artifacts: dict[str, Any] | None = None
    state: dict[str, Any] | None = None

def initialize_challenge(service, deployer: str, player_address: str) -> ChallengeInitResult:
    initial_funding = service.config.deployer_starting_balance
    player_funding = service.config.player_starting_balance
    compiled = service.compile_package()

    publish = service.client(deployer).transaction(initial_sender=SuiAddress(deployer))
    upgrade_cap = publish.builder.publish(
        compiled["modules"],
        [bcs.Address.from_str(dependency) for dependency in compiled["dependencies"]],
    )
    publish.transfer_objects(transfers=[upgrade_cap], recipient=SuiAddress(deployer))
    publish_result = publish.execute()
    if publish_result.is_err():
        raise SuiCTFSandboxError("transaction execution failed", {"cause": publish_result.result_string})
    publish_result = publish_result.result_data

    package_id = service.object_changes_by_type(publish_result, "published")[0]
    house_object_id = service.object_changes_by_type(publish_result, "created", "::trx_gambling_house::House")[0]
    admin_cap_id = service.object_changes_by_type(publish_result, "created", "::trx_gambling_house::HouseAdminCap")[0]

    init = service.client(deployer).transaction(initial_sender=SuiAddress(deployer))
    funding_coin = init.split_coin(coin=init.gas, amounts=[initial_funding])
    init.move_call(
        target=f"{package_id}::trx_gambling_house::init_house",
        arguments=[ObjectID(admin_cap_id), ObjectID(house_object_id), funding_coin],
    )
    init_result = init.execute()
    if init_result.is_err():
        raise SuiCTFSandboxError("transaction execution failed", {"cause": init_result.result_string})

    fund = service.client(deployer).transaction(initial_sender=SuiAddress(deployer))
    player_coin = fund.split_coin(coin=fund.gas, amounts=[player_funding])
    fund.transfer_objects(transfers=[player_coin], recipient=SuiAddress(player_address))
    fund_result = fund.execute()
    if fund_result.is_err():
        raise SuiCTFSandboxError("transaction execution failed", {"cause": fund_result.result_string})

    return ChallengeInitResult(
        artifacts={
            "package_id": package_id,
            "house_object_id": house_object_id,
        },
    )

def check_solve_conditions(service, instance: dict) -> dict:
    result = service.client().get_gas(SuiAddress(instance["player_address"]), fetch_all=True)
    if result.is_err():
        raise SuiCTFSandboxError("failed to fetch player balance", {"cause": result.result_string})
    current_balance = sum(int(coin.balance) for coin in result.result_data.data)
    if current_balance < service.config.target_balance:
        return {"error": "challenge not solved yet"}
    return {"flag": service.config.flag}
