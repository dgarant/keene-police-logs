
create table dispatcher
(
    id serial primary key,
    "number" int,
    first_name varchar(50),
    last_name varchar(50)
);

create table officer
(
    id serial primary key,
    "number" int,
    last_name varchar(50),
    first_name varchar(50)
);


create table incident
(
    id serial primary key,
    report_id varchar(10),
    dispatch_time timestamp,
    dispatch_source varchar(50),
    category varchar(50),
    outcome varchar(50),

    call_taker_id int references dispatcher(id),
    primary_officer_id int references officer(id),

    location varchar(300),
    latitude decimal(8, 6),
    longitude decimal(8, 6),
    jurisdiction varchar(100),
    aux_event_type varchar(100),
    aux_event_key varchar(100),
    geocode_failed bit,
    formatted_location varchar(500)
);

create table summons
(
    id serial primary key,

    incident_id int references incident(id) not null,
    first_name varchar(100),
    last_name varchar(100),
    age_at_summons int,
    charges varchar(100),
    address varchar(100)
);

create table arrest
(
    id serial primary key,

    incident_id int references incident(id) not null,
    first_name varchar(100),
    last_name varchar(100),
    age_at_arrest int,
    charges varchar(100),
    address varchar(100)
);

create table protective_custody
(
    id serial primary key,

    incident_id int references incident(id) not null,
    first_name varchar(100),
    last_name varchar(100),
    address varchar(300),
    age_at_custody int,
    charges varchar(100)
);

create table location_change
(
    id serial primary key,
    incident_id int references incident(id) not null,
    location varchar(300),
    change_date date
);

create table responding_officer
(
    id serial primary key,
    incident_id int references incident(id) not null,
    officer_id int references officer(id) not null,
    dispatch_time timestamp,
    arrival_time timestamp,
    cleared_time timestamp
);
