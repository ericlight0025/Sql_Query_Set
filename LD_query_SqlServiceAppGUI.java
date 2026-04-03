package com.javalight.oa.service.sql.generator;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Container;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Font;
import java.awt.GridBagConstraints;
import java.awt.GridBagLayout;
import java.awt.Insets;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.stream.Collectors;

import javax.swing.BorderFactory;
import javax.swing.Box;
import javax.swing.BoxLayout;
import javax.swing.JButton;
import javax.swing.JComponent;
import javax.swing.JFileChooser;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.SwingUtilities;
import javax.swing.SwingWorker;
import javax.swing.UIManager;
import javax.swing.border.EmptyBorder;
import javax.swing.border.LineBorder;
import javax.swing.border.TitledBorder;

public class LD_query_SqlServiceAppGUI extends JFrame {

    private static final long serialVersionUID = 1L;

    // Dark Mode 色票
    private static final Color BG_COLOR = new Color(24, 26, 27);
    private static final Color PANEL_COLOR = new Color(34, 36, 38);
    private static final Color INPUT_COLOR = new Color(44, 47, 51);
    private static final Color BTN_COLOR = new Color(64, 114, 255);
    private static final Color BTN_HOVER_COLOR = new Color(88, 132, 255);
    private static final Color TEXT_COLOR = new Color(230, 230, 230);
    private static final Color BORDER_COLOR = new Color(80, 80, 80);
    private static final Color LOG_COLOR = new Color(20, 20, 20);

    private JTextField txtOutputPath;
    private JTextField txtSqlFilePath;
    private JTextField txtContent;
    private JTextField txtAuthor;
    private JTextField txtTitleFilePath;
    private JTextField txtOaNo;
    private JTextField txtQueryTemplate;
    private JTextArea txtLog;
    private JButton btnBrowseOutputPath;
    private JButton btnBrowseSqlFile;
    private JButton btnBrowseTitleFile;
    private JButton btnExecute;

    public LD_query_SqlServiceAppGUI() {
        initializeUI();
    }

    private void initializeUI() {
        setTitle("SQL 管理工具 - GUI 版本");
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setSize(900, 720);
        setLocationRelativeTo(null);
        setResizable(true);

        JPanel mainPanel = new JPanel();
        mainPanel.setLayout(new BoxLayout(mainPanel, BoxLayout.Y_AXIS));
        mainPanel.setBorder(new EmptyBorder(15, 15, 15, 15));

        JLabel titleLabel = new JLabel("SQL 管理工具");
        titleLabel.setFont(new Font("微軟正黑體", Font.BOLD, 18));
        mainPanel.add(titleLabel);
        mainPanel.add(Box.createVerticalStrut(10));

        JPanel inputPanel = new JPanel();
        inputPanel.setLayout(new GridBagLayout());
        inputPanel.setBorder(BorderFactory.createTitledBorder("輸入欄位"));

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(5, 5, 5, 5);
        int row = 0;

        // OA No
        gbc.gridx = 0;
        gbc.gridy = row;
        gbc.weightx = 0;
        inputPanel.add(new JLabel("OA 號碼:"), gbc);
        gbc.gridx = 1;
        gbc.weightx = 1;
        txtOaNo = new JTextField("1141202337-00", 30);
        inputPanel.add(txtOaNo, gbc);
        row++;

        // Query Template
        gbc.gridx = 0;
        gbc.gridy = row;
        gbc.weightx = 0;
        inputPanel.add(new JLabel("Query 範本:"), gbc);
        gbc.gridx = 1;
        gbc.weightx = 1;
        txtQueryTemplate = new JTextField("001-ph-LDNCS2WKARDQUERY_Update", 30);
        inputPanel.add(txtQueryTemplate, gbc);
        row++;

        // Output Path
        gbc.gridx = 0;
        gbc.gridy = row;
        gbc.weightx = 0;
        inputPanel.add(new JLabel("輸出路徑:"), gbc);
        gbc.gridx = 1;
        gbc.weightx = 1;
        JPanel outputPathPanel = new JPanel(new BorderLayout(5, 0));
        txtOutputPath = new JTextField("U:/3.download-U-To-PC/1150302061-指定代理人-陳姿秀/", 25);
        outputPathPanel.add(txtOutputPath, BorderLayout.CENTER);
        btnBrowseOutputPath = new JButton("瀏覽...");
        btnBrowseOutputPath.addActionListener(e -> browseFolder());
        outputPathPanel.add(btnBrowseOutputPath, BorderLayout.EAST);
        inputPanel.add(outputPathPanel, gbc);
        row++;

        // SQL File Path
        gbc.gridx = 0;
        gbc.gridy = row;
        gbc.weightx = 0;
        inputPanel.add(new JLabel("SQL 檔案:"), gbc);
        gbc.gridx = 1;
        gbc.weightx = 1;
        JPanel sqlFilePanel = new JPanel(new BorderLayout(5, 0));
        txtSqlFilePath = new JTextField("U:/3.download-U-To-PC/1150302061-指定代理人-陳姿秀/001-ph-lonoticeitemTest.sql", 25);
        sqlFilePanel.add(txtSqlFilePath, BorderLayout.CENTER);
        btnBrowseSqlFile = new JButton("瀏覽...");
        btnBrowseSqlFile.addActionListener(e -> browseSqlFile());
        sqlFilePanel.add(btnBrowseSqlFile, BorderLayout.EAST);
        inputPanel.add(sqlFilePanel, gbc);
        row++;

        // Content
        gbc.gridx = 0;
        gbc.gridy = row;
        gbc.weightx = 0;
        inputPanel.add(new JLabel("內容:"), gbc);
        gbc.gridx = 1;
        gbc.weightx = 1;
        txtContent = new JTextField("計算ESG效益，撈取契約變更案件明細_陳姿秀", 30);
        inputPanel.add(txtContent, gbc);
        row++;

        // Author
        gbc.gridx = 0;
        gbc.gridy = row;
        gbc.weightx = 0;
        inputPanel.add(new JLabel("作者:"), gbc);
        gbc.gridx = 1;
        gbc.weightx = 1;
        txtAuthor = new JTextField("陳OO", 30);
        inputPanel.add(txtAuthor, gbc);
        row++;

        // Title File Path
        gbc.gridx = 0;
        gbc.gridy = row;
        gbc.weightx = 0;
        inputPanel.add(new JLabel("欄位檔案:"), gbc);
        gbc.gridx = 1;
        gbc.weightx = 1;
        JPanel titleFilePanel = new JPanel(new BorderLayout(5, 0));
        txtTitleFilePath = new JTextField("U:/3.download-U-To-PC/1150302061-XXXXXX/欄位.txt", 25);
        titleFilePanel.add(txtTitleFilePath, BorderLayout.CENTER);
        btnBrowseTitleFile = new JButton("瀏覽...");
        btnBrowseTitleFile.addActionListener(e -> browseTitleFile());
        titleFilePanel.add(btnBrowseTitleFile, BorderLayout.EAST);
        inputPanel.add(titleFilePanel, gbc);

        mainPanel.add(inputPanel);
        mainPanel.add(Box.createVerticalStrut(15));

        JPanel buttonPanel = new JPanel(new FlowLayout(FlowLayout.CENTER, 10, 0));
        btnExecute = new JButton("執行");
        btnExecute.setFont(new Font("微軟正黑體", Font.PLAIN, 14));
        btnExecute.setPreferredSize(new Dimension(100, 40));
        btnExecute.addActionListener(e -> executeProcess());
        buttonPanel.add(btnExecute);
        mainPanel.add(buttonPanel);
        mainPanel.add(Box.createVerticalStrut(15));

        JPanel logPanel = new JPanel(new BorderLayout());
        logPanel.setBorder(BorderFactory.createTitledBorder("執行日誌"));
        txtLog = new JTextArea(10, 60);
        txtLog.setEditable(false);
        txtLog.setFont(new Font("Monospaced", Font.PLAIN, 11));
        JScrollPane scrollPane = new JScrollPane(txtLog);
        logPanel.add(scrollPane, BorderLayout.CENTER);
        mainPanel.add(logPanel);

        JScrollPane mainScrollPane = new JScrollPane(mainPanel);
        mainScrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        add(mainScrollPane);

        applyDarkMode(mainPanel, mainScrollPane, titleLabel, inputPanel, buttonPanel, logPanel);
    }

    private void applyDarkMode(JPanel mainPanel, JScrollPane mainScrollPane, JLabel titleLabel,
                               JPanel inputPanel, JPanel buttonPanel, JPanel logPanel) {
        getContentPane().setBackground(BG_COLOR);

        mainPanel.setBackground(BG_COLOR);
        inputPanel.setBackground(PANEL_COLOR);
        buttonPanel.setBackground(BG_COLOR);
        logPanel.setBackground(PANEL_COLOR);

        titleLabel.setForeground(TEXT_COLOR);

        styleComponentTree(mainPanel);
        styleScrollPane(mainScrollPane);
        styleTitledBorder(inputPanel);
        styleTitledBorder(logPanel);

        txtLog.setBackground(LOG_COLOR);
        txtLog.setForeground(TEXT_COLOR);
        txtLog.setCaretColor(TEXT_COLOR);
        txtLog.setSelectionColor(BTN_COLOR);
        txtLog.setSelectedTextColor(Color.WHITE);

        styleButton(btnExecute);
        styleButton(btnBrowseOutputPath);
        styleButton(btnBrowseSqlFile);
        styleButton(btnBrowseTitleFile);
    }

    private void styleComponentTree(Component comp) {
        if (comp instanceof JPanel) {
            comp.setBackground(PANEL_COLOR);
            if (comp instanceof JComponent) {
                styleTitledBorder((JComponent) comp);
            }
        }

        if (comp instanceof JLabel) {
            comp.setForeground(TEXT_COLOR);
            comp.setBackground(PANEL_COLOR);
        }

        if (comp instanceof JTextField) {
            JTextField field = (JTextField) comp;
            field.setBackground(INPUT_COLOR);
            field.setForeground(TEXT_COLOR);
            field.setCaretColor(TEXT_COLOR);
            field.setSelectionColor(BTN_COLOR);
            field.setSelectedTextColor(Color.WHITE);
            field.setBorder(BorderFactory.createCompoundBorder(
                new LineBorder(BORDER_COLOR, 1, true),
                BorderFactory.createEmptyBorder(6, 8, 6, 8)
            ));
        }

        if (comp instanceof JTextArea) {
            JTextArea area = (JTextArea) comp;
            area.setBackground(INPUT_COLOR);
            area.setForeground(TEXT_COLOR);
            area.setCaretColor(TEXT_COLOR);
            area.setSelectionColor(BTN_COLOR);
            area.setSelectedTextColor(Color.WHITE);
            area.setBorder(BorderFactory.createCompoundBorder(
                new LineBorder(BORDER_COLOR, 1, true),
                BorderFactory.createEmptyBorder(6, 8, 6, 8)
            ));
        }

        if (comp instanceof JButton) {
            styleButton((JButton) comp);
        }

        if (comp instanceof JScrollPane) {
            styleScrollPane((JScrollPane) comp);
        }

        if (comp instanceof Container) {
            for (Component child : ((Container) comp).getComponents()) {
                styleComponentTree(child);
            }
        }
    }

    private void styleButton(JButton button) {
        button.setBackground(BTN_COLOR);
        button.setForeground(Color.WHITE);
        button.setFocusPainted(false);
        button.setBorder(BorderFactory.createCompoundBorder(
            new LineBorder(BTN_HOVER_COLOR, 1, true),
            BorderFactory.createEmptyBorder(8, 14, 8, 14)
        ));
    }

    private void styleScrollPane(JScrollPane scrollPane) {
        scrollPane.getViewport().setBackground(BG_COLOR);
        scrollPane.setBackground(BG_COLOR);
        scrollPane.setBorder(BorderFactory.createLineBorder(BORDER_COLOR));
    }

    private void styleTitledBorder(JComponent component) {
        if (component.getBorder() instanceof TitledBorder) {
            TitledBorder titledBorder = (TitledBorder) component.getBorder();
            titledBorder.setTitleColor(TEXT_COLOR);
            titledBorder.setBorder(BorderFactory.createLineBorder(BORDER_COLOR));
        }
    }

    private void browseFolder() {
        JFileChooser chooser = new JFileChooser();
        chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
        chooser.setCurrentDirectory(new File(txtOutputPath.getText().isEmpty() ? "U:/" : txtOutputPath.getText()));
        int returnVal = chooser.showOpenDialog(this);
        if (returnVal == JFileChooser.APPROVE_OPTION) {
            String selectedPath = chooser.getSelectedFile().getAbsolutePath();
            if (!selectedPath.endsWith(File.separator)) {
                selectedPath += File.separator;
            }
            txtOutputPath.setText(selectedPath);
            appendLog("選擇了資料夾: " + selectedPath);
        }
    }

    private void browseSqlFile() {
        JFileChooser chooser = new JFileChooser();
        chooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        chooser.setCurrentDirectory(new File(
            txtSqlFilePath.getText().isEmpty() ? "U:/" : new File(txtSqlFilePath.getText()).getParent()
        ));
        int returnVal = chooser.showOpenDialog(this);
        if (returnVal == JFileChooser.APPROVE_OPTION) {
            String selectedFile = chooser.getSelectedFile().getAbsolutePath();
            txtSqlFilePath.setText(selectedFile);
            appendLog("選擇了 SQL 檔案: " + selectedFile);
        }
    }

    private void browseTitleFile() {
        JFileChooser chooser = new JFileChooser();
        chooser.setFileSelectionMode(JFileChooser.FILES_ONLY);
        chooser.setCurrentDirectory(new File(
            txtTitleFilePath.getText().isEmpty() ? "U:/" : new File(txtTitleFilePath.getText()).getParent()
        ));
        int returnVal = chooser.showOpenDialog(this);
        if (returnVal == JFileChooser.APPROVE_OPTION) {
            String selectedFile = chooser.getSelectedFile().getAbsolutePath();
            txtTitleFilePath.setText(selectedFile);
            appendLog("選擇了欄位檔案: " + selectedFile);
        }
    }

    private void executeProcess() {
        txtLog.setText("");

        if (!validateInputs()) {
            return;
        }

        SwingWorker<Void, String> worker = new SwingWorker<Void, String>() {
            @Override
            protected Void doInBackground() throws Exception {
                try {
                    runSqlByIO();
                    publish("✓ 執行成功!");
                } catch (Exception e) {
                    publish("✗ 執行失敗: " + e.getMessage());
                    e.printStackTrace();
                }
                return null;
            }

            @Override
            protected void process(java.util.List<String> chunks) {
                for (String chunk : chunks) {
                    appendLog(chunk);
                }
            }
        };
        worker.execute();
    }

    private boolean validateInputs() {
        String outputPath = txtOutputPath.getText().trim();
        String sqlFilePath = txtSqlFilePath.getText().trim();
        String titleFilePath = txtTitleFilePath.getText().trim();

        if (outputPath.isEmpty()) {
            appendLog("✗ 錯誤: 輸出路徑不能為空");
            return false;
        }
        if (sqlFilePath.isEmpty()) {
            appendLog("✗ 錯誤: SQL 檔案路徑不能為空");
            return false;
        }
        if (titleFilePath.isEmpty()) {
            appendLog("✗ 錯誤: 欄位檔案路徑不能為空");
            return false;
        }

        File sqlFile = new File(sqlFilePath);
        if (!sqlFile.exists()) {
            appendLog("✗ 錯誤: SQL 檔案不存在: " + sqlFilePath);
            return false;
        }

        File titleFile = new File(titleFilePath);
        if (!titleFile.exists()) {
            appendLog("✗ 錯誤: 欄位檔案不存在: " + titleFilePath);
            return false;
        }

        if (txtContent.getText().trim().isEmpty()) {
            appendLog("✗ 錯誤: 內容不能為空");
            return false;
        }
        if (txtAuthor.getText().trim().isEmpty()) {
            appendLog("✗ 錯誤: 作者不能為空");
            return false;
        }

        return true;
    }

    private void runSqlByIO() throws Exception {
        appendLog("開始執行...");

        String oaNo = txtOaNo.getText().trim();
        String querytemplate = txtQueryTemplate.getText().trim();
        String outputPath = txtOutputPath.getText().trim();
        String sqlFilePath = txtSqlFilePath.getText().trim();
        String content = txtContent.getText().trim();
        String author = txtAuthor.getText().trim();
        String titleFilePath = txtTitleFilePath.getText().trim();

        if (!outputPath.endsWith(File.separator) && !outputPath.endsWith("/")) {
            outputPath += "/";
        }

        String sqlString = Files.readString(Paths.get(sqlFilePath), StandardCharsets.UTF_8);
        String title = readTitleFileAndJoinByDoublePipe(titleFilePath);

        SimpleDateFormat sdFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.000000");
        String sysdate = sdFormat.format(new Date());

        String templatePath = "D:\\JAVA_DEV\\Util-New\\SeleniumOA-v2\\src\\main\\resources\\templates\\ManagerSql.sql";
        String templateContent = Files.readString(Paths.get(templatePath), StandardCharsets.UTF_8);

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
        Files.writeString(Paths.get(outputFilepath), filledContent, StandardCharsets.UTF_8);

        appendLog("OA 號碼: " + oaNo);
        appendLog("Query 範本: " + querytemplate);
        appendLog("輸出路徑: " + outputPath);
        appendLog("SQL 檔案: " + sqlFilePath);
        appendLog("欄位檔案: " + titleFilePath);
        appendLog("輸出檔案: " + outputFilepath);
    }

    private String readTitleFileAndJoinByDoublePipe(String titleFilePath) throws Exception {
        List<String> lines = Files.readAllLines(Paths.get(titleFilePath), StandardCharsets.UTF_8);
        return lines.stream()
            .map(String::trim)
            .filter(s -> !s.isEmpty())
            .collect(Collectors.joining("||"));
    }

    private String escapeSqlLiteral(String text) {
        if (text == null) {
            return "";
        }
        return text.replace("'", "''");
    }

    private String buildSqlClobExpression(String sqlText) {
        if (sqlText == null || sqlText.isEmpty()) {
            return "to_clob('')";
        }

        java.util.List<String> lines = splitLinesPreservingSeparators(sqlText);
        java.util.List<String> clobBlocks = new java.util.ArrayList<>();

        for (int start = 0; start < lines.size(); start += 10) {
            int end = Math.min(start + 10, lines.size());
            clobBlocks.add(buildSingleToClobBlock(lines, start, end));
        }

        return String.join(" || ", clobBlocks);
    }

    private String buildSingleToClobBlock(java.util.List<String> lines, int start, int end) {
        StringBuilder content = new StringBuilder();
        for (int i = start; i < end; i++) {
            content.append(lines.get(i));
        }

        return "to_clob('" + escapeSqlLiteral(content.toString()) + "')";
    }

    private java.util.List<String> splitLinesPreservingSeparators(String text) {
        java.util.List<String> lines = new java.util.ArrayList<>();
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

    private void appendLog(String message) {
        txtLog.append(message + "\n");
        txtLog.setCaretPosition(txtLog.getDocument().getLength());
    }

    private static void setupGlobalDarkDefaults() {
        UIManager.put("Panel.background", PANEL_COLOR);
        UIManager.put("OptionPane.background", PANEL_COLOR);
        UIManager.put("OptionPane.messageForeground", TEXT_COLOR);
        UIManager.put("Label.foreground", TEXT_COLOR);
        UIManager.put("TextField.background", INPUT_COLOR);
        UIManager.put("TextField.foreground", TEXT_COLOR);
        UIManager.put("TextArea.background", INPUT_COLOR);
        UIManager.put("TextArea.foreground", TEXT_COLOR);
        UIManager.put("Button.background", BTN_COLOR);
        UIManager.put("Button.foreground", Color.WHITE);
        UIManager.put("FileChooser.background", PANEL_COLOR);
    }

    public static void main(String[] args) {
        setupGlobalDarkDefaults();

        SwingUtilities.invokeLater(() -> {
            LD_query_SqlServiceAppGUI frame = new LD_query_SqlServiceAppGUI();
            frame.setVisible(true);
        });
    }
}