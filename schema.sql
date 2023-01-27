CREATE TABLE IF NOT EXISTS translations (
    target TEXT, 
    message TEXT, 
    trans TEXT, 
    PRIMARY KEY (target, message)
);