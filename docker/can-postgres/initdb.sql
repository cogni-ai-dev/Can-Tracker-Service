CREATE SCHEMA IF NOT EXISTS can_tracker AUTHORIZATION can;

GRANT ALL PRIVILEGES ON SCHEMA can_tracker TO can;

ALTER ROLE can IN DATABASE can SET search_path = can_tracker, public;
ALTER DATABASE can SET search_path = can_tracker, public;
