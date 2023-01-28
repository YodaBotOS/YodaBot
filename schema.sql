CREATE TABLE IF NOT EXISTS translations (
    target TEXT, 
    message TEXT, 
    trans TEXT, 
    ttl TIMESTAMPTZ DEFAULT now() + interval '1 month',
    PRIMARY KEY (target, message)
);