CREATE TABLE IF NOT EXISTS webhook_events (
    id          BIGSERIAL PRIMARY KEY,
    event_type  TEXT        NOT NULL,
    action      TEXT,
    repo        TEXT,
    sender      TEXT,
    payload     JSONB       NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- One row per watched repo, tells the deployer where to deploy
CREATE TABLE IF NOT EXISTS projects (
    id              BIGSERIAL PRIMARY KEY,
    repo            TEXT        NOT NULL UNIQUE,  -- e.g. "you/myapp"
    deploy_host     TEXT        NOT NULL,          -- SSH host
    deploy_user     TEXT        NOT NULL DEFAULT 'deploy',
    deploy_workdir  TEXT        NOT NULL,          -- e.g. /srv/myapp
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS deployments (
    id              BIGSERIAL PRIMARY KEY,
    project_id      BIGINT      REFERENCES projects(id),
    repo            TEXT        NOT NULL,
    status          TEXT        NOT NULL DEFAULT 'queued',
    triggered_by    TEXT,
    triggered_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS deployment_logs (
    id              BIGSERIAL PRIMARY KEY,
    deployment_id   BIGINT      NOT NULL REFERENCES deployments(id),
    seq             INT         NOT NULL,
    line            TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deployments_repo        ON deployments (repo);
CREATE INDEX IF NOT EXISTS idx_deployments_status      ON deployments (status);
CREATE INDEX IF NOT EXISTS idx_deployment_logs_dep_seq ON deployment_logs (deployment_id, seq);

-- Seed a project so the first push actually triggers a deploy
-- INSERT INTO projects (repo, deploy_host, deploy_user, deploy_workdir)
-- VALUES ('you/myapp', '10.0.0.5', 'deploy', '/srv/myapp');
