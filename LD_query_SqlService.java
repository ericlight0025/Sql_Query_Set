package com.javalight.oa.service.sql.generator;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;

// 配套管理
public class LD_query_SqlService {

    public static void main(String[] args) throws Exception {
        if (args != null && args.length > 0) {
            runsqlByIO(args[0]);
        } else {
            runsqlByIO((String) null);
        }
    }

    /**
     * 主方法支援從外部傳入 titleFilePath（例如前端或命令列），若為 null 或空字串則使用預設值
     */
    public static void runsqlByIO(String titleFilePathArg) throws Exception {
        String oaNo = "1141202337-00";
        String querytemplate = "001-ph-LDNCS2WKARDQUERY_Update";
        String outputPath = "U:/3.download-U-To-PC/1150302061-XXXXX";
        String sqlFilePath = "U:/3.download-U-To-PC/1150302061-XXXXX/001-ph-lonoticeitemTest.sql";
        String content = "計算OOOOO";
        String author = "陳OO";
        String titleFilePath = titleFilePathArg == null || titleFilePathArg.trim().isEmpty()
            ? "U:/3.download-U-To-PC/1150302061-OOOOO/欄位.txt"
            : titleFilePathArg.trim();

        if (!outputPath.endsWith("/") && !outputPath.endsWith("\\")) {
            outputPath += "/";
        }

        String sqlString = Files.readString(Paths.get(sqlFilePath), StandardCharsets.UTF_8);
        String title = readTitleFileAndJoinByDoublePipe(titleFilePath);

        SimpleDateFormat sdFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.000000");
        String sysdate = sdFormat.format(new Date());

        Path templatePath = Paths.get("D:/JAVA_DEV/Util-New/SeleniumOA-v2/src/main/resources/templates/ManagerSql.sql");
        String templateContent = Files.readString(templatePath, StandardCharsets.UTF_8);

        String sqlClobExpression = buildSqlClobExpression(sqlString);

        String filledContent = templateContent
            .replace("${querytemplate}", escapeSqlLiteral(querytemplate))
            .replace("${oaNo}", escapeSqlLiteral(oaNo))
            .replace("'${sqlScript}'", sqlClobExpression)
            .replace("${content}", escapeSqlLiteral(content))
            .replace("${author}", escapeSqlLiteral(author))
            .replace("${title}", escapeSqlLiteral(title))
            .replace("${sysdate}", sysdate);

        String outputFilepath = outputPath + querytemplate + ".sql";

        try (Writer writer = new OutputStreamWriter(
                new FileOutputStream(outputFilepath),
                StandardCharsets.UTF_8)) {
            writer.write(filledContent);
            System.out.println("輸出成功: " + outputFilepath);
        } catch (IOException e) {
            System.err.println("寫入 SQL 檔案失敗：" + e.getMessage());
        }
    }

    public static String readTitleFileAndJoinByDoublePipe(String titleFilePath) throws IOException {
        List<String> lines = Files.readAllLines(Paths.get(titleFilePath), StandardCharsets.UTF_8);
        List<String> cleanedParts = new ArrayList<>();

        for (String line : lines) {
            String trimmed = line.trim();
            if (!trimmed.isEmpty()) {
                cleanedParts.add(trimmed);
            }
        }

        return String.join("||", cleanedParts);
    }

    public static String escapeSqlLiteral(String text) {
        if (text == null) {
            return "";
        }
        return text.replace("'", "''");
    }

    public static String buildSqlClobExpression(String sqlText) {
        if (sqlText == null || sqlText.isEmpty()) {
            return "to_clob('')";
        }

        List<String> lines = splitLinesPreservingSeparators(sqlText);
        List<String> blocks = new ArrayList<>();

        for (int start = 0; start < lines.size(); start += 10) {
            int end = Math.min(start + 10, lines.size());
            blocks.add(buildSingleToClobBlock(lines, start, end));
        }

        return String.join(" || ", blocks);
    }

    private static String buildSingleToClobBlock(List<String> lines, int start, int end) {
        StringBuilder content = new StringBuilder();
        for (int i = start; i < end; i++) {
            content.append(lines.get(i));
        }

        String escaped = escapeSqlLiteral(content.toString());
        return "to_clob('" + escaped + "')";
    }

    private static List<String> splitLinesPreservingSeparators(String text) {
        List<String> lines = new ArrayList<>();
        int start = 0;

        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);
            if (ch == '\r') {
                if (i + 1 < text.length() && text.charAt(i + 1) == '\n') {
                    i++;
                }
                lines.add(text.substring(start, i + 1));
                start = i + 1;
            } else if (ch == '\n') {
                lines.add(text.substring(start, i + 1));
                start = i + 1;
            }
        }

        if (start < text.length()) {
            lines.add(text.substring(start));
        }

        if (lines.isEmpty()) {
            lines.add(text);
        }

        return lines;
    }
}
