module trx_gambling_house::trx_gambling_house {

use sui::hex;
use std::debug;
use sui::event;
use sui::sui::SUI;
use sui::coin::{Self, Coin};
use std::string::{Self, String};
use sui::balance::{Self, Balance};
use sui::random::{Self, Random};
use sui::vec_set::{Self, VecSet};
use trx_gambling_house::cards::{Self, Card};
use trx_gambling_house::utils;

const E_INSUFFICIENT_DEPOSIT: u64 = 0x1;
const E_INVALID_SETTEEMEZZO_STRATEGY: u64 = 0xf;
const E_INVALID_SUPERENALOTTO_PICKS: u64 = 0x10;
const E_LETITRIDE: u64 = 0x11;
const E_ALREADY_INITIALIZED: u64 = 0x12;
const E_INVALID_INITIAL_FUNDING: u64 = 0x13;

const RANDOM_FLAG_GAME: u64 = 0;
const LET_IT_RIDE_GAME: u64 = 1;
const SUPERENALOTTO_GAME: u64 = 2;
const SETTEEMEZZO_GAME: u64 = 3;

public struct RandomFlag has copy, drop, store {}
public struct LetItRide has copy, drop, store {}
public struct SuperEnalotto has copy, drop, store {}
public struct SetteEMezzo has copy, drop, store {}

public struct Game has store {
    prize_pool: Balance<SUI>,
    ticket_price: u64,
}
public struct GameEvent<phantom G> has copy, drop {
    payout: u64,
}
public struct GameReceipt<phantom G, D> has key, store {
    id: UID,
    data: D,
}

public struct House has key, store {
    id: UID,
    games: vector<Game>,
    initialized: bool,
}

public struct HouseAdminCap has key, store {
    id: UID,
}

fun init(ctx: &mut TxContext) {
    transfer::share_object(
        House {
            id: object::new(ctx),
            games: vector[
                create_game<RandomFlag>(utils::mist_from_sui(0)),
                create_game<LetItRide>(utils::mist_from_sui(50)),
                create_game<SuperEnalotto>(utils::mist_from_sui(50)),
                create_game<SetteEMezzo>(utils::mist_from_sui(50)),
            ],
            initialized: false,
        }
    );
    transfer::transfer(HouseAdminCap { id: object::new(ctx) }, ctx.sender());
}

public fun init_house(owner_cap: HouseAdminCap, house: &mut House, funding: Coin<SUI>, ctx: &mut TxContext) {
    let game_count = house.games.length();
    assert!(!house.initialized, E_ALREADY_INITIALIZED);
    assert!(coin::value(&funding) % game_count == 0, E_INVALID_INITIAL_FUNDING);

    let mut funding = funding;
    let share = coin::value(&funding) / game_count;
    let mut i = 0;
    while (i + 1 < game_count) {
        fund_game_pool(&mut house.games[i], coin::split(&mut funding, share, ctx));
        i = i + 1;
    };
    fund_game_pool(&mut house.games[i], funding);
    house.initialized = true;

    let HouseAdminCap { id } = owner_cap;
    id.delete();
}

fun create_game<G>(ticket_price: u64): Game {
    Game { prize_pool: balance::zero(), ticket_price }
}

fun fund_game_pool(game: &mut Game, funding: Coin<SUI>) {
    coin::put(&mut game.prize_pool, funding);
}

fun buy_ticket(game: &mut Game, deposit: &mut Coin<SUI>, ctx: &mut TxContext) {
    assert!(coin::value(deposit) >= game.ticket_price, E_INSUFFICIENT_DEPOSIT);
    let ticket = coin::split(deposit, game.ticket_price, ctx);
    coin::put(&mut game.prize_pool, ticket);
}

fun new_game_receipt<G: store, D: store>(data: D, ctx: &mut TxContext): GameReceipt<G, D> {
    GameReceipt { id: object::new(ctx), data }
}

fun send_game_receipt<G: store, D: store>(data: D, ctx: &mut TxContext) {
    let receipt = new_game_receipt<G, D>(data, ctx);
    transfer::public_transfer(receipt, ctx.sender());
}

// you might as well try lol
entry fun get_random_flag(r: &Random, house: &mut House, deposit: &mut Coin<SUI>, ctx: &mut TxContext) {
    buy_ticket(&mut house.games[RANDOM_FLAG_GAME], deposit, ctx);
    let mut g = random::new_generator(r, ctx);
    let body = hex::encode(g.generate_bytes(8));
    let mut flag = string::utf8(b"TRX{");
    flag.append_utf8(body);
    flag.append_utf8(b"}");
    send_game_receipt<RandomFlag, String>(flag, ctx);
}

// https://www.youtube.com/shorts/VYXAND8enUo
entry fun all_in_on_17_black(r: &Random, house: &mut House, deposit: &mut Coin<SUI>, number: u8, ctx: &mut TxContext): Coin<SUI> {
    let game = &mut house.games[LET_IT_RIDE_GAME];
    buy_ticket(game, deposit, ctx);
    assert!(number == 17, E_LETITRIDE);
    let mut g = random::new_generator(r, ctx);
    let spin = g.generate_u8() % 37;
    if (spin == number) {
        let mut payout = coin::take(
            &mut game.prize_pool,
            35 * game.ticket_price,
            ctx,
        );
        // Ļ̷̛͖͉͎̤̤͔̩̻̥̟̮̗̲͚̠͓̻̩͈͇̍̃͂̀̈́̐͑̀͊̇́͂͌́̓͊̔́̾̌̆̈͌͑̇́̏͝ͅE̸̢̨̲̪͈͈̭͉̞̯̩͎̳̥̻͈̙̦̝͔͚̿̂̉Ṱ̶̡̣̦̯̭̝̥͕̪̭͙͎͓̖̜̼̱͇̰̲͎̲͎̫̥̠̼͒̉͒̄̎̽̀̇̀̽̏͒̆͛̕͠ͅͅ ̷̛̺̙̟̺̯̟̟͇̠̱̩͔̗͇͈̥̣͎͈̥̱̭̦̓́͛̂̿̈́̃͗̀̃̌̉̿͛̇̉͘͘̕͝͝I̵̳͑̎̑̚Ț̸̲̙͉̻̣̳̮̦̙̠̹̟͈̭͔͔̘͇̣͓̺͂͗̂̔̆̆̄̉̋̚ͅ ̵̢̢̡̟͔͓̪̲̭̗̫̻̜͖̪̭̐̊͛́͘͘͝R̴̛͕̦̯̞͉̮̺͓̱̱̰̲̞̞̰̟͔̅͒̈́̿̏̏͒̔͊͆̾̅̓͑̎̏́́̊͊͊̈̓̉͆̚̕̕͝Į̶̛̘̖̝̦̲̤̙̗͖̤̀̓̄͆̑͋̓̏̄͋̍̀̓̋̾̏̃̒̈́͗̓̓͑̃̈́͘̕͠Ḑ̵̭͕̱̜̬̗̮͚̼̺̬̪̭̪̱̜̩̺̠̪͖̯̤͉͙̙͉̙̅̐̄͂̈́̽̄̾͋̂̈́ͅĘ̶̫̘̭̞̥͚̬̺͗̈́̃̎͑̓̊̂̐̌̍͝
        let next = all_in_on_17_black(r, house, deposit, number, ctx);
        coin::join(&mut payout, next);
        event::emit(GameEvent<LetItRide> { payout: payout.value() });
        payout
    } else {
        debug::print(&string::utf8(b"phuck vegas"));
        abort E_LETITRIDE
    }
}

// are you italian enough? https://it.wikipedia.org/wiki/SuperEnalotto
entry fun superenalotto(r: &Random, house: &mut House, deposit: &mut Coin<SUI>, numbers: vector<u8>, ctx: &mut TxContext): Coin<SUI> {
    let game = &mut house.games[SUPERENALOTTO_GAME];
    buy_ticket(game, deposit, ctx);
    let guess_set: VecSet<u8> = vec_set::from_keys(numbers);
    assert!(vec_set::length(&guess_set) == 6, E_INVALID_SUPERENALOTTO_PICKS);
    let mut g = random::new_generator(r, ctx);
    let mut superenalotto_nums = vector::tabulate!(90, |i| ((i + 1) as u8));
    random::shuffle(&mut g, &mut superenalotto_nums);
    let winning_set = superenalotto_nums.take(6);
    let matches = winning_set.count!(
        |e| vec_set::contains(&guess_set, e)
    );
    let jackpot = balance::value(&game.prize_pool);
    let payout_amount = match (matches) {
        2 => 2 * game.ticket_price,
        3 => 20 * game.ticket_price,
        4 => 1_000 * game.ticket_price,
        5 => 100_000 * game.ticket_price,
        6 => jackpot,
        _ => 0,
    };
    send_game_receipt<SuperEnalotto, vector<u8>>(winning_set, ctx);
    if (payout_amount > 0) event::emit(GameEvent<SuperEnalotto> { payout: payout_amount });
    return coin::take(&mut game.prize_pool, payout_amount, ctx)
}

// we play ts with grandpa at christmas🔥 https://it.wikipedia.org/wiki/Sette_e_mezzo 
entry fun setteemezzo(r: &Random, house: &mut House, deposit: &mut Coin<SUI>, hit_until: u8, ctx: &mut TxContext): Coin<SUI> {
    let game = &mut house.games[SETTEEMEZZO_GAME];
    buy_ticket(game, deposit, ctx);
    assert!(hit_until <= 15, E_INVALID_SETTEEMEZZO_STRATEGY);

    let mut deck = cards::setteemezzo_create_deck();
    cards::shuffle_deck(&mut deck, r, ctx);

    let mut player_hand = vector[];
    let mut dealer_hand = vector[];
    player_hand.push_back(cards::draw_card(&mut deck));
    dealer_hand.push_back(cards::draw_card(&mut deck));

    let player_total = cards::draw_until(&mut deck, &mut player_hand, hit_until);
    let dealer_total = cards::draw_until(&mut deck, &mut dealer_hand, 10);
    let payout_amount =
        if (utils::setteemezzo_is_bust(player_total)) 0
        else if (utils::setteemezzo_is_sette_reale(&player_hand, player_total)) 3 * game.ticket_price
        else if (dealer_total < player_total || utils::setteemezzo_is_bust(dealer_total)) 2 * game.ticket_price
        else 0;

    if (payout_amount > 0) event::emit(GameEvent<SetteEMezzo> { payout: payout_amount });
    send_game_receipt<SetteEMezzo, vector<vector<Card>>>(vector[player_hand, dealer_hand], ctx);
    return coin::take(&mut game.prize_pool, payout_amount, ctx)
}
}
