SELECT
    to_clob('L01') ||
    'L02' ||
    'L03' ||
    'L04' ||
    'L05' ||
    'L06' ||
    'L07' ||
    'L08' ||
    'L09' ||
    'L10' ||
    to_clob('L11') ||
    'L12' ||
    'L13' ||
    'L14' ||
    'L15' ||
    'L16' ||
    'L17' ||
    'L18' ||
    'L19' ||
    'L20' ||
    to_clob('L21') ||
    'L22' ||
    'L23' ||
    'L24' ||
    'L25' ||
    'L26' ||
    'L27' ||
    'L28' AS demo_text
FROM dual
where date1 between '?startDate?' and '?endDate?'
;
