select * FROM LIS.LDOOOO WHERE QUERYTEMPLATE='1151234567-00';
DELETE FROM LIS.LDOOOO WHERE QUERYTEMPLATE='1151234567-00';
INSERT INTO LIS.LDOOOO
(QUERYTEMPLATE, QUERYSQL, REMARK, SPAREFIELD1, SPAREFIELD2, SPAREFIELD3, SYSMAKEDATE, SYSMODIFYDATE)
VALUES('1151234567-00', to_clob('SELECT
    to_clob(''L01'') ||
    ''L02'' ||
    ''L03'' ||
    ''L04'' ||
    ''L05'' ||
    ''L06'' ||
    ''L07'' ||
    ''L08'' ||
    ''L09'' ||
') || to_clob('    ''L10'' ||
    to_clob(''L11'') ||
    ''L12'' ||
    ''L13'' ||
    ''L14'' ||
    ''L15'' ||
    ''L16'' ||
    ''L17'' ||
    ''L18'' ||
    ''L19'' ||
') || to_clob('    ''L20'' ||
    to_clob(''L21'') ||
    ''L22'' ||
    ''L23'' ||
    ''L24'' ||
    ''L25'' ||
    ''L26'' ||
    ''L27'' ||
    ''L28'' AS demo_text
FROM dual
') || to_clob('where date1 between ''?startDate?'' and ''?endDate?''
;
'), '查詢內容-(陳OO)', NULL, '欄位一||欄位二', NULL, TIMESTAMP '2026-04-03 22:16:04.000000', TIMESTAMP '2026-04-03 22:16:04.000000');
select * FROM LIS.LDOOOO WHERE QUERYTEMPLATE='1151234567-00';
