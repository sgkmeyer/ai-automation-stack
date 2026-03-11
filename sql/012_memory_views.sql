SET search_path TO memory, public;

CREATE OR REPLACE VIEW entry_with_entities AS
SELECT
    e.id,
    e.entry_type,
    e.body,
    e.structured,
    e.source,
    e.source_ref,
    e.occurred_at,
    e.created_at,
    COALESCE(
        json_agg(
            json_build_object(
                'entity_id', ent.id,
                'name', ent.name,
                'type', ent.entity_type,
                'role', ee.role
            )
        ) FILTER (WHERE ent.id IS NOT NULL),
        '[]'::json
    ) AS entities
FROM entries e
LEFT JOIN entry_entities ee ON ee.entry_id = e.id
LEFT JOIN entities ent ON ent.id = ee.entity_id
GROUP BY e.id;

CREATE OR REPLACE VIEW entity_timeline AS
SELECT
    ent.id AS entity_id,
    ent.name AS entity_name,
    ent.entity_type,
    e.id AS entry_id,
    e.entry_type,
    e.body,
    e.occurred_at,
    e.source,
    ee.role
FROM entities ent
JOIN entry_entities ee ON ee.entity_id = ent.id
JOIN entries e ON e.id = ee.entry_id
ORDER BY ent.id, e.occurred_at DESC;
