-- create the DB
drop database if exists groupproject;
create database GroupProject;

-- use the DB
use GroupProject;

-- drop tables if they exist
-- need to drop in opposite order of create due to foreign key constraints
drop table if exists coach_application_decision;
drop table if exists disable_account;
drop table if exists user_ban;
drop table if exists exercise_changes;
drop table if exists message;
DROP TABLE IF EXISTS meal_plans;
DROP TABLE IF EXISTS weekly_meals;
drop table if exists plan_exercise;
drop table if exists workout_plans;
drop table if exists created_workout; 
drop table if exists exercises; -- done
drop table if exists coach_certifications; 
drop table if exists coach_reviews; 
drop table if exists coach_subscriptions; 
drop table if exists coach_requests;
drop table if exists coach_reports;
drop table if exists daily_survey; 
drop table if exists coach_profiles; 
drop table if exists coach_bios;
drop table if exists user_payment; 
drop table if exists payment_details; 
drop table if exists user_profiles; 
drop table if exists goals; 
drop table if exists user_login; 
drop table if exists users; 

-- user tables
-- creates the overall parent user table

create table Users(
	User_ID integer auto_increment not null,
	role ENUM('A', 'C', 'U') default 'U' not null, -- A: admin, C: Coach, U: User
	is_banned boolean default false, -- determine if account is banned
	is_disabled boolean default false, -- determine if account is disabled
	create_date datetime default CURRENT_TIMESTAMP, -- date user account was created
	last_update datetime default CURRENT_TIMESTAMP, -- last update of user
	primary key (user_id)
);

-- store user login credentials

create table User_login(
    username varchar(32) not null, -- username for user
	password_hash varchar(255) not null, -- user pass word
	user_id integer, -- link login with users
	primary key (user_id),
	foreign key (user_id) references users(user_id)
);

-- Defines the users goals

create table Goals(
	User_ID integer not null,
	goal_weight float not null, -- the targer weight of the user
	goal_type ENUM('Strength', 'Weightloss', 'Stamina'), -- pre determined goals
	Information text,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key(User_id),
    foreign key (user_id) references users(user_id)
);

-- displayable information user profile information

create table User_Profiles(
	user_id integer not null,
	first_name varchar(16) not null,
	last_name varchar(16) not null,
	birthday date,
	profile_picture_url text, -- store URL for users profile img
	current_weight float not null, -- the current weight of the user
	create_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key (user_id),
	foreign key (user_id) references users(user_id)
);

-- users payment credentials

create table payment_details(
	user_id integer not null,
	card_num varchar(32) not null,
	CVV integer not null,
	exp_month integer not null, -- experation month
	exp_year integer not null, -- experation year
	create_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key (user_id),
    foreign key (user_id) references users(user_id)
);

-- store user progress pictures
create table Progress_Pictures(
    picture_id integer auto_increment not null,
    user_id integer not null,
    image_url text not null,
    create_date datetime default CURRENT_TIMESTAMP,
    primary key (picture_id),
    foreign key (user_id) references Users(user_id) ON DELETE CASCADE
);

-- coach tables

-- define coach profile

create table Coach_Profiles(
	coach_id integer auto_increment not null,
	user_id integer not null, -- coaches are also users so they get a user_id
	bio text,
	is_nutritionist boolean default false not null, -- determine if coach is a nutritionist
	is_active integer default 1 not null, -- determine if coach is still active
	pricing decimal(10,2) default 24.99 not null, -- determine coach's price
	create_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key (coach_id),
	foreign key (user_id) references Users(user_id)
);

create table coach_availability(
    availability_id integer auto_increment not null,
    coach_id integer not null, -- link to coach
    DOW ENUM('M', 'T', 'W', 'TH', 'F', 'SAT', 'SUN') NOT NULL,
    start_time time not null, -- start time of availability
    end_time time not null, -- end time of availability
    create_date datetime default CURRENT_TIMESTAMP,
    last_update datetime default CURRENT_TIMESTAMP,
    primary key (availability_id),
    foreign key (coach_id) references coach_profiles(coach_id)
);

-- store user daily surveys

create table Daily_Survey(
	survey_id integer auto_increment not null,
	user_id integer not null, -- link survey to user
	result integer not null, -- 1-5
	date datetime default CURRENT_TIMESTAMP,
	primary key (survey_id),
	foreign key (user_id) references users(user_id)
);

-- store user to coach applications

create table Coach_requests(
	request_id integer auto_increment not null,
	user_id integer not null, -- link to coach
	coach_id integer not null, -- link to coach getting requested
    comment text, -- comment from user on why they want to be coached by this coach
	status ENUM('pending', 'rejected', 'accepted') default 'pending' not null, -- determines the state of the users request to coach
	create_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key (request_id),
	foreign key (user_id) references users(user_id),
	foreign key (coach_id) references coach_profiles(coach_id)
);

create table coach_subscriptions(
	subscription_id integer auto_increment not null,
	user_id integer not null, -- link to coach
	coach_id integer not null, -- link to coach getting requested,
	start_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key (subscription_id),
	foreign key (user_id) references users(user_id),
	foreign key (coach_id) references coach_profiles(coach_id)
);

-- store reviews of a coach

create table Coach_reviews(
	review_id integer auto_increment not null,
	user_id integer, -- users that wrote review
	coach_id integer not null, -- coach that the review is on
	rating integer not null, -- 1-5 stars
	comment text, -- optional text
	create_date datetime default CURRENT_TIMESTAMP,
	primary key (review_id),
	foreign key (user_id) references users(user_id),
	foreign key (coach_id) references coach_profiles(coach_id)
);

-- certifications of a coach

create table coach_certifications(
	certification_id integer auto_increment not null,
	coach_id integer not null, -- link to a coach
	file_url text not null, -- link to the application file
	status ENUM('pending', 'rejected', 'accepted') default 'pending' not null, -- status of coaching application
	create_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key (certification_id),
	foreign key (coach_id) references coach_profiles(coach_id)
);

-- coach reports
create table coach_reports(
    report_id integer auto_increment not null,
    reporter_id integer not null,
    coach_id integer not null,
    reason text not null,
    status ENUM('pending', 'reviewed', 'dismissed') default 'pending' not null,
    create_date datetime default CURRENT_TIMESTAMP(),
    last_update datetime default CURRENT_TIMESTAMP(),
    primary key (report_id),
    foreign key (reporter_id) references users(user_id),
    foreign key (coach_id) references coach_profiles(coach_id)
);

-- workout tables
-- hold exercise information

create table exercises(
	exercise_id integer auto_increment not null,
	name varchar(32) not null, -- name of exercise
	muscle_group ENUM('Back', 'Bicep', 'Tricep', 'Legs', 'Chest', 'Abs', 'Cardio', 'Shoulders'), --  muscle group that workout targets
	equipment_needed ENUM('Machine', 'Free Weight', 'Body Weight'),
	video_url text, -- link to video demonstration of exercise
	create_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
    is_removed BOOLEAN DEFAULT FALSE,
	primary key (exercise_id)
);

-- stores workouts created for a user

create table created_workout(
	create_id integer auto_increment not null,
	user_id integer not null, -- user the workout is for
	coach_id integer, -- if there is a value that means a coach made it for the user
	primary key (create_id),
	foreign key (user_id) references users(user_id),
	foreign key (coach_id) references coach_profiles(coach_id)
);

-- 

create table workout_plans(
	plan_id integer auto_increment not null,
	create_id integer not null,
	title varchar(16) not null,
	create_date datetime default CURRENT_TIMESTAMP,
	last_update datetime default CURRENT_TIMESTAMP,
	primary key(plan_id),
	foreign key (create_id) references created_workout(create_id)	
);


create table plan_exercise(
	plan_exercise_id integer auto_increment not null,
	plan_id integer not null,
	exercise_id integer,
	sets integer,
	reps integer,
	is_template boolean default false,
	primary key (plan_exercise_id),
	foreign key (plan_id) references workout_plans(plan_id),
	foreign key (exercise_id) references exercises(exercise_id)
);

-- create weekly diet plans
CREATE TABLE weekly_meals(
	weekly_meals_id integer auto_increment NOT NULL,
	coach_id integer,
	user_id integer,
	PRIMARY KEY (weekly_meals_id),
	FOREIGN KEY (user_id) REFERENCES users(user_id),
	foreign KEY (coach_id) REFERENCES coach_profiles(coach_id)
);

-- store coach mode nutirition plans
CREATE TABLE meal_plans(
	meal_id integer auto_increment NOT NULL,
	DOW ENUM('M', 'T', 'W', 'TH', 'F', 'SAT', 'SUN') NOT NULL,
	meal text NOT NULL,
	weekly_meal_id integer NOT NULL, -- select which weekly plan meal belongs to
	PRIMARY KEY (meal_id),
	foreign KEY (weekly_meal_id) REFERENCES weekly_meals(weekly_meals_id) 
);

-- stores messages and determines who is receiving the message

create table message(
	message_id integer auto_increment not null,
	sender_id integer not null, -- sender of message
	receiver_id integer not null, -- id of the receiving user
	content text not null, -- body of the message
	timestamp datetime default CURRENT_TIMESTAMP,
	primary key (message_id),
	foreign key (sender_id) references users(user_id),
	foreign key (receiver_id) references users(user_id)
);


-- admin audit tables

-- track admin changes to exercise

create table exercise_changes(
	change_id integer auto_increment not null,
	admin_id integer not null, -- admin that changed an exercise,
	exercise_id integer not null,-- exercise that was changed
	event ENUM('delete', 'edit', 'add') not null,
	create_date datetime default CURRENT_TIMESTAMP,
	primary key (change_id),
	foreign key (admin_id) references users(user_id),
	foreign key (exercise_id) references exercises(exercise_id)
);


create table user_ban(
	ban_id integer auto_increment not null,
	admin_id integer not null, -- admin that disabled account
	user_id integer not null, -- user that was disabled
	reason text,
	create_date datetime default CURRENT_TIMESTAMP,
	primary key (ban_id),
	foreign key (admin_id) references users(user_id),
	foreign key (user_id) references users(user_id)
);


create table disable_account(
	disable_id integer auto_increment not null,
	admin_id integer not null, -- admin that disabled account
	user_id integer not null, -- user that was disabled
	reason text,
	-- when the disabled account gets re-activated
	day integer not null,
	month integer not null,
	year integer not null,
	create_date datetime default CURRENT_TIMESTAMP,
	primary key (disable_id),
	foreign key (admin_id) references users(user_id),
	foreign key (user_id) references users(user_id)
);


create table coach_application_decision(
	app_id integer auto_increment not null,
	coach_id integer not null, -- coach that had certification reviewed
	certification_id integer not null, -- certification that wes reviewed
	admin_id integer not null, -- admin that reviewed certification
	decision ENUM('pending', 'rejected', 'accepted'), -- decision after review
	primary key (app_id),
	foreign key (coach_id) references coach_profiles(coach_id),
	foreign key (certification_id) references coach_certifications(certification_id),
	foreign key (admin_id) references users(user_id)
);