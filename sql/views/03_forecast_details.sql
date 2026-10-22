CREATE OR REPLACE VIEW vw_forecast_details AS
SELECT
    f.forecast_id,
    f.product_id,
    p.product_name,
    p.category,
    f.forecast_month,
    f.forecast_qty,
    f.actual_qty,
    f.actual_qty - f.forecast_qty AS variance_qty,
    ABS(f.actual_qty - f.forecast_qty) AS absolute_variance_qty,
    ROUND(
        ABS(f.actual_qty - f.forecast_qty)::numeric
        / NULLIF(f.actual_qty, 0) * 100,
        2
    ) AS absolute_percentage_error
FROM forecasts AS f
JOIN products AS p
    ON f.product_id = p.product_id;