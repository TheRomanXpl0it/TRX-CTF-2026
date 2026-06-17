module trx_gambling_house::cards {

use sui::random::{Self, Random};

public enum Suit has copy, drop, store { Cups, Coins, Swords, Clubs }
public enum Rank has copy, drop, store { Ace, Num(u8), Jack, Knight, King }

public struct Card has copy, drop, store {
    suit: Suit,
    rank: Rank,
}

public struct Deck has copy, drop {
    cards: vector<Card>,
}

fun setteemezzo_card_value(card: Card): u8 {
    match (card.rank) {
        Rank::Ace => 2,
        Rank::Num(n) => 2 * n,
        Rank::Jack | Rank::Knight | Rank::King => 1,
    }
}

fun setteemezzo_hand_value(hand: vector<Card>): u8 {
    vector::fold!(hand, 0u8, |acc, card| acc + setteemezzo_card_value(card))
}

public(package) fun setteemezzo_create_deck(): Deck {
    let cards = vector::tabulate!(40, |i| {
        let suit = match (i / 10) {
            0 => Suit::Cups,
            1 => Suit::Coins,
            2 => Suit::Swords,
            _ => Suit::Clubs,
        };
        let rank_idx = (i % 10) as u8;
        let rank = match (rank_idx) {
            0 => Rank::Ace,
            1 | 2 | 3 | 4 | 5 | 6 => Rank::Num(rank_idx + 1),
            7 => Rank::Jack,
            8 => Rank::Knight,
            _ => Rank::King,
        };
        Card { suit, rank }
    });
    Deck { cards }
}

public(package) fun shuffle_deck(deck: &mut Deck, random: &Random, ctx: &mut TxContext) {
    let mut g = random::new_generator(random, ctx);
    random::shuffle(&mut g, &mut deck.cards);
}

public(package) fun draw_card(deck: &mut Deck): Card {
    deck.cards.pop_back()
}

public(package) fun draw_until(deck: &mut Deck, hand: &mut vector<Card>, stop_at: u8): u8 {
    let mut total = setteemezzo_hand_value(*hand);
    while (total < stop_at) {
        hand.push_back(draw_card(deck));
        total = setteemezzo_hand_value(*hand);
    };
    total
}
}
