module trx_gambling_house::utils {

use trx_gambling_house::cards::Card;

const MIST_PER_SUI: u64 = 1_000_000_000;

public(package) fun mist_from_sui(amount: u64): u64 {
    amount * MIST_PER_SUI
}

public(package) fun setteemezzo_is_bust(total: u8): bool {
    total > 15
}

public(package) fun setteemezzo_is_sette_reale(hand: &vector<Card>, total: u8): bool {
    total == 15 && hand.length() == 2
}
}
