-- =====================================================================
-- EventHive : Event Ticketing and Attendance Analytics
-- schema.sql  (MySQL 8.0)   -- normalised to 3NF, 8 tables, 1 view, 2 triggers
-- =====================================================================
DROP DATABASE IF EXISTS eventhive;
CREATE DATABASE eventhive CHARACTER SET utf8mb4;
USE eventhive;

-- ---------- lookup / master tables ----------
CREATE TABLE organisers (
  organiser_id INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(100) NOT NULL,
  email        VARCHAR(120) NOT NULL UNIQUE,
  phone        VARCHAR(15)
) ENGINE=InnoDB;

CREATE TABLE venues (
  venue_id   INT AUTO_INCREMENT PRIMARY KEY,
  venue_name VARCHAR(120) NOT NULL,
  city       VARCHAR(60)  NOT NULL,
  capacity   INT NOT NULL,
  CONSTRAINT chk_venue_capacity CHECK (capacity > 0)
) ENGINE=InnoDB;

CREATE TABLE event_types (
  event_type_id INT AUTO_INCREMENT PRIMARY KEY,
  type_name     VARCHAR(40) NOT NULL UNIQUE
) ENGINE=InnoDB;

CREATE TABLE attendees (
  attendee_id INT AUTO_INCREMENT PRIMARY KEY,
  full_name   VARCHAR(100) NOT NULL,
  email       VARCHAR(120) NOT NULL UNIQUE,
  city        VARCHAR(60)
) ENGINE=InnoDB;

-- ---------- events and tickets ----------
CREATE TABLE events (
  event_id      INT AUTO_INCREMENT PRIMARY KEY,
  organiser_id  INT NOT NULL,
  venue_id      INT NOT NULL,
  event_type_id INT NOT NULL,
  event_name    VARCHAR(150) NOT NULL,
  event_date    DATE NOT NULL,
  start_time    TIME NOT NULL,
  capacity      INT NOT NULL,                     -- seats released for this event
  status        ENUM('SCHEDULED','COMPLETED','CANCELLED') NOT NULL DEFAULT 'SCHEDULED',
  CONSTRAINT chk_event_capacity CHECK (capacity > 0),
  FOREIGN KEY (organiser_id)  REFERENCES organisers(organiser_id),
  FOREIGN KEY (venue_id)      REFERENCES venues(venue_id),
  FOREIGN KEY (event_type_id) REFERENCES event_types(event_type_id)
) ENGINE=InnoDB;

CREATE TABLE ticket_types (
  ticket_type_id INT AUTO_INCREMENT PRIMARY KEY,
  event_id       INT NOT NULL,
  tier_name      VARCHAR(30) NOT NULL,            -- Early Bird / Standard / VIP
  price          DECIMAL(10,2) NOT NULL,
  quantity_total INT NOT NULL,
  sale_start     DATE NOT NULL,
  CONSTRAINT chk_tt_price CHECK (price >= 0),
  CONSTRAINT chk_tt_qty   CHECK (quantity_total > 0),
  UNIQUE (event_id, tier_name),
  FOREIGN KEY (event_id) REFERENCES events(event_id)
) ENGINE=InnoDB;

-- ---------- transactions ----------
CREATE TABLE bookings (
  booking_id     INT AUTO_INCREMENT PRIMARY KEY,
  attendee_id    INT NOT NULL,
  ticket_type_id INT NOT NULL,
  booked_at      DATETIME NOT NULL,
  status         ENUM('CONFIRMED','CANCELLED') NOT NULL DEFAULT 'CONFIRMED',
  cancelled_at   DATETIME NULL,
  CONSTRAINT chk_cancel CHECK (status = 'CONFIRMED' OR cancelled_at IS NOT NULL),
  FOREIGN KEY (attendee_id)    REFERENCES attendees(attendee_id),
  FOREIGN KEY (ticket_type_id) REFERENCES ticket_types(ticket_type_id),
  INDEX idx_booking_tt (ticket_type_id, status)
) ENGINE=InnoDB;

CREATE TABLE checkins (
  checkin_id   INT AUTO_INCREMENT PRIMARY KEY,
  booking_id   INT NOT NULL UNIQUE,                -- one check-in per ticket
  checkin_time DATETIME NOT NULL,
  FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
) ENGINE=InnoDB;

-- =====================================================================
-- VIEW : one row per event with sales, revenue, attendance
-- =====================================================================
CREATE VIEW v_event_summary AS
SELECT e.event_id, e.event_name, et.type_name AS event_type, v.venue_name, v.city,
       e.event_date, e.capacity,
       COUNT(CASE WHEN b.status = 'CONFIRMED' THEN 1 END)             AS tickets_sold,
       COALESCE(SUM(CASE WHEN b.status = 'CONFIRMED' THEN t.price END), 0) AS revenue,
       COUNT(c.checkin_id)                                            AS attended
FROM events e
JOIN event_types et      ON et.event_type_id = e.event_type_id
JOIN venues v            ON v.venue_id = e.venue_id
JOIN ticket_types t      ON t.event_id = e.event_id
LEFT JOIN bookings b     ON b.ticket_type_id = t.ticket_type_id
LEFT JOIN checkins c     ON c.booking_id = b.booking_id
GROUP BY e.event_id, e.event_name, et.type_name, v.venue_name, v.city, e.event_date, e.capacity;

-- =====================================================================
-- TRIGGERS
-- =====================================================================
DELIMITER $$

-- 1) Prevent overselling: a CONFIRMED booking is rejected if the ticket tier
--    OR the whole event is already full.
CREATE TRIGGER trg_prevent_overselling
BEFORE INSERT ON bookings
FOR EACH ROW
BEGIN
  DECLARE tier_sold  INT;  DECLARE tier_max  INT;
  DECLARE event_sold INT;  DECLARE event_max INT;  DECLARE ev INT;

  IF NEW.status = 'CONFIRMED' THEN
    SELECT quantity_total, event_id INTO tier_max, ev
      FROM ticket_types WHERE ticket_type_id = NEW.ticket_type_id;
    SELECT COUNT(*) INTO tier_sold FROM bookings
      WHERE ticket_type_id = NEW.ticket_type_id AND status = 'CONFIRMED';
    SELECT capacity INTO event_max FROM events WHERE event_id = ev;
    SELECT COUNT(*) INTO event_sold FROM bookings b
      JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
      WHERE t.event_id = ev AND b.status = 'CONFIRMED';

    IF tier_sold >= tier_max THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Sold out: ticket tier is full';
    ELSEIF event_sold >= event_max THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Sold out: event capacity reached';
    END IF;
  END IF;
END$$

-- 2) Only CONFIRMED tickets can be checked in.
CREATE TRIGGER trg_checkin_validate
BEFORE INSERT ON checkins
FOR EACH ROW
BEGIN
  DECLARE s VARCHAR(20);
  SELECT status INTO s FROM bookings WHERE booking_id = NEW.booking_id;
  IF s <> 'CONFIRMED' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot check in a cancelled booking';
  END IF;
END$$

DELIMITER ;
