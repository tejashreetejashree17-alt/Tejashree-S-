-- =====================================================================
-- EventHive : queries.sql (MySQL 8.0)
-- Part A = DML (booking / cancellation / check-in)   Part B = analytics
-- =====================================================================
USE eventhive;

-- ---------------------------- PART A : DML ----------------------------
-- A1. Book a ticket (attendee 10 buys tier 2 of event 1)
INSERT INTO bookings (attendee_id, ticket_type_id, booked_at, status)
VALUES (10, 2, NOW(), 'CONFIRMED');

-- A2. Cancel that booking (seat is released: only CONFIRMED rows count as sold)
UPDATE bookings SET status = 'CANCELLED', cancelled_at = NOW()
WHERE booking_id = LAST_INSERT_ID();

-- A3. Check an attendee in at the gate
INSERT INTO checkins (booking_id, checkin_time) VALUES (1, NOW());

-- A4. Trigger demo: fill a tier, then try one more booking -> error 1644 'Sold out'
--     (pick a tier with a small quota, e.g. ticket_type_id = 3 (VIP, event 1))
-- INSERT INTO bookings (attendee_id, ticket_type_id, booked_at) VALUES (11, 3, NOW());

-- ------------------------- PART B : ANALYTICS -------------------------
-- Q1. Tickets sold per day before the event, by event type (booking curve)
SELECT et.type_name AS event_type,
       DATEDIFF(e.event_date, DATE(b.booked_at)) AS days_before_event,
       COUNT(*) AS tickets_sold
FROM bookings b
JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
JOIN events e       ON e.event_id = t.event_id
JOIN event_types et ON et.event_type_id = e.event_type_id
WHERE b.status = 'CONFIRMED' AND e.status = 'COMPLETED'
GROUP BY et.type_name, days_before_event
ORDER BY et.type_name, days_before_event DESC;

-- Q2. No-show rate by event type (confirmed tickets with no check-in)
SELECT et.type_name AS event_type,
       COUNT(*)                         AS confirmed_tickets,
       COUNT(c.checkin_id)              AS attended,
       ROUND(100.0 * (COUNT(*) - COUNT(c.checkin_id)) / COUNT(*), 1) AS no_show_pct
FROM bookings b
JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
JOIN events e       ON e.event_id = t.event_id
JOIN event_types et ON et.event_type_id = e.event_type_id
LEFT JOIN checkins c ON c.booking_id = b.booking_id
WHERE b.status = 'CONFIRMED' AND e.status = 'COMPLETED'
GROUP BY et.type_name
ORDER BY no_show_pct DESC;

-- Q3. Revenue by event type and venue (top 10 combinations)
SELECT et.type_name AS event_type, v.venue_name, v.city,
       COUNT(*) AS tickets, SUM(t.price) AS revenue
FROM bookings b
JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
JOIN events e       ON e.event_id = t.event_id
JOIN event_types et ON et.event_type_id = e.event_type_id
JOIN venues v       ON v.venue_id = e.venue_id
WHERE b.status = 'CONFIRMED'
GROUP BY et.type_name, v.venue_name, v.city
ORDER BY revenue DESC
LIMIT 10;

-- Q4. Top 5 events by sell-through (uses the view + window function)
SELECT * FROM (
  SELECT event_name, event_type, capacity, tickets_sold,
         ROUND(100.0 * tickets_sold / capacity, 1) AS sell_through_pct,
         RANK() OVER (ORDER BY 1.0 * tickets_sold / capacity DESC) AS rnk
  FROM v_event_summary
  WHERE event_date < CURDATE()
) ranked
WHERE rnk <= 5;

-- Q5. Sales velocity: average tickets per day between first sale and event day
SELECT e.event_name, et.type_name AS event_type,
       COUNT(*) AS tickets_sold,
       DATEDIFF(e.event_date, DATE(MIN(b.booked_at))) + 1 AS selling_days,
       ROUND(1.0 * COUNT(*) / (DATEDIFF(e.event_date, DATE(MIN(b.booked_at))) + 1), 2) AS tickets_per_day
FROM bookings b
JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
JOIN events e       ON e.event_id = t.event_id
JOIN event_types et ON et.event_type_id = e.event_type_id
WHERE b.status = 'CONFIRMED' AND e.status = 'COMPLETED'
GROUP BY e.event_id, e.event_name, et.type_name, e.event_date
ORDER BY tickets_per_day DESC
LIMIT 10;

-- Q6. Ticket tier performance: volume, revenue and no-show rate
SELECT t.tier_name,
       COUNT(*)            AS tickets_sold,
       SUM(t.price)        AS revenue,
       ROUND(100.0 * (COUNT(*) - COUNT(c.checkin_id)) / COUNT(*), 1) AS no_show_pct
FROM bookings b
JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
JOIN events e       ON e.event_id = t.event_id
LEFT JOIN checkins c ON c.booking_id = b.booking_id
WHERE b.status = 'CONFIRMED' AND e.status = 'COMPLETED'
GROUP BY t.tier_name
ORDER BY revenue DESC;

-- Q7. Cancellation rate by event type
SELECT et.type_name AS event_type, COUNT(*) AS bookings,
       SUM(b.status = 'CANCELLED') AS cancelled,
       ROUND(100.0 * SUM(b.status = 'CANCELLED') / COUNT(*), 1) AS cancel_pct
FROM bookings b
JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
JOIN events e       ON e.event_id = t.event_id
JOIN event_types et ON et.event_type_id = e.event_type_id
GROUP BY et.type_name
ORDER BY cancel_pct DESC;

-- Q8. Share of tickets sold in the final 7 days vs earlier (pricing signal)
SELECT et.type_name AS event_type,
       ROUND(100.0 * SUM(DATEDIFF(e.event_date, DATE(b.booked_at)) <= 7) / COUNT(*), 1) AS last_week_pct,
       ROUND(100.0 * SUM(DATEDIFF(e.event_date, DATE(b.booked_at)) > 30) / COUNT(*), 1)  AS early_30plus_pct
FROM bookings b
JOIN ticket_types t ON t.ticket_type_id = b.ticket_type_id
JOIN events e       ON e.event_id = t.event_id
JOIN event_types et ON et.event_type_id = e.event_type_id
WHERE b.status = 'CONFIRMED' AND e.status = 'COMPLETED'
GROUP BY et.type_name
ORDER BY last_week_pct DESC;
