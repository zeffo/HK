CREATE TABLE IF NOT EXISTS Tags (keyword TEXT Primary Key, meta TEXT);
CREATE TABLE IF NOT EXISTS Playlists (
    id SERIAL PRIMARY KEY,
    name TEXT,
    owner BIGINT,
    uses INTEGER DEFAULT 0,
    UNIQUE(name, owner)
);

CREATE TABLE IF NOT EXISTS Tracks (
    id TEXT PRIMARY KEY,
    title TEXT,
    stream TEXT
);

CREATE TABLE IF NOT EXISTS PlaylistTrackRelation (
    id SERIAL PRIMARY KEY,
    track TEXT REFERENCES Tracks(id),
    playlist INTEGER REFERENCES Playlists(id) ON DELETE CASCADE,
    UNIQUE(track, playlist)
);
                