CREATE TABLE IF NOT EXISTS translations (
    target TEXT, 
    message TEXT, 
    trans TEXT, 
    ttl TIMESTAMPTZ DEFAULT now() + interval '1 month',
    PRIMARY KEY (target, message)
);

CREATE TABLE IF NOT EXISTS chat(
    id SERIAL,
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    messages JSON NOT NULL,
    created TIMESTAMPTZ DEFAULT now(),
    ttl TIMESTAMPTZ DEFAULT now() + interval '3 minutes',
    is_google BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (id, user_id, channel_id)
);