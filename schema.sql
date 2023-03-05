CREATE TABLE IF NOT EXISTS translations (
    target TEXT, 
    message TEXT, 
    trans TEXT, 
    ttl TIMESTAMPTZ DEFAULT now() + interval '1 month',
    PRIMARY KEY (target, message)
);

CREATE TABLE IF NOT EXISTS chat(
    id SERIAL PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    messages JSON[] NOT NULL DEFAULT '[]',
    created TIMESTAMPTZ DEFAULT now(),
    ttl TIMESTAMPTZ DEFAULT now() + interval '3 minutes',
    PRIMARY KEY (user_id, channel_id)
);