Current Schema for Database

```sql
create extension if not exists btree_gist;

-- Reference data
create table currencies (
    code char(3) primary key
);

create table brokers (
    id   smallint generated always as identity primary key,
    name text not null unique
);

create table asset_types (
    id   smallint generated always as identity primary key,
    name text not null unique          -- 'equity', 'etf', 'option', 'crypto'
);

create table txn_types (
    code     text primary key,         -- 'buy', 'sell', 'dividend', ...
    category text not null check (category in ('trade', 'cash'))
);

create table fee_types (
    id   smallint generated always as identity primary key,
    name text not null unique          -- 'commission', 'sec_fee', 'regulatory'
);

-- Entities
create table accounts (
    id        bigint generated always as identity primary key,
    broker_id smallint not null references brokers(id),
    label     text not null,
    unique (broker_id, label)
);

create table securities (
    id            bigint generated always as identity primary key,
    asset_type_id smallint not null references asset_types(id),
    name          text not null,
    currency      char(3) not null references currencies(code)
);

-- Tickers are an attribute of a security over time, not its identity
create table security_tickers (
    security_id bigint not null references securities(id),
    ticker      varchar(15) not null,
    valid_from  date not null,
    valid_to    date,
    primary key (security_id, valid_from),
    check (valid_to is null or valid_to > valid_from),
    exclude using gist (
        security_id with =,
        daterange(valid_from, valid_to) with &&
    )
);

-- Supertype: facts common to every transaction
create table transactions (
    id            bigint generated always as identity primary key,
    account_id    bigint not null references accounts(id),
    txn_type      text not null references txn_types(code),
    trade_date    date not null,
    settle_date   date,
    broker_txn_id text,
    notes         text,
    unique (id, txn_type),                          -- target for subtype FKs
    unique (account_id, broker_txn_id),             -- safe CSV re-imports
    check (settle_date is null or settle_date >= trade_date)
);

-- Subtype: buys and sells
create table trades (
    txn_id      bigint primary key,
    txn_type    text not null check (txn_type in ('buy', 'sell')),
    security_id bigint not null references securities(id),
    quantity    numeric(18,8) not null check (quantity > 0),
    price       numeric(14,4) not null check (price >= 0),   -- per share
    currency    char(3) not null references currencies(code),
    foreign key (txn_id, txn_type) references transactions(id, txn_type)
);

-- Subtype: dividends, interest, deposits, withdrawals
create table cash_events (
    txn_id      bigint primary key,
    txn_type    text not null
                check (txn_type in ('dividend', 'interest', 'deposit', 'withdrawal')),
    security_id bigint references securities(id),   -- null for deposits etc.
    amount      numeric(18,4) not null,
    currency    char(3) not null references currencies(code),
    foreign key (txn_id, txn_type) references transactions(id, txn_type)
);

-- Zero or more fees per transaction
create table transaction_fees (
    txn_id      bigint not null references transactions(id),
    fee_type_id smallint not null references fee_types(id),
    amount      numeric(12,4) not null check (amount >= 0),
    currency    char(3) not null references currencies(code),
    primary key (txn_id, fee_type_id)
);

-- Splits belong to the security, not to any account
create table splits (
    security_id    bigint not null references securities(id),
    effective_date date not null,
    ratio_num      integer not null check (ratio_num > 0),
    ratio_den      integer not null check (ratio_den > 0),
    primary key (security_id, effective_date)
);

create index on transactions (account_id, trade_date);
create index on trades (security_id);
```