/**
 * JAIN RIASEC — Google Apps Script
 * Handles: saving survey results, saving enrollments, reading sheet data
 * 
 * SETUP:
 * 1. Open Google Sheets → Extensions → Apps Script
 * 2. Paste this entire file, replacing any existing code
 * 3. Click Deploy → New Deployment → Web App
 *    - Execute as: Me
 *    - Who has access: Anyone
 * 4. Copy the deployment URL into your .env as SCRIPT_URL
 * 5. Re-deploy every time you change this code (Manage Deployments → Edit → New Version)
 */

// ── Sheet names ──────────────────────────────────────────────────────────────
var RESULTS_SHEET    = 'Sheet1';       // survey results go here
var ENROLLMENT_SHEET = 'Enrollments';  // enrollment/scholarship requests

// ── Column headers for Sheet1 ────────────────────────────────────────────────
var RESULTS_HEADERS = [
  'Timestamp', 'Name', 'Email', 'Phone',
  'R', 'I', 'A', 'S', 'E', 'C',
  'Top3 Codes', 'Top3 Names'
];

// ── Column headers for Enrollments ───────────────────────────────────────────
var ENROLLMENT_HEADERS = [
  'Timestamp', 'Name', 'Email', 'Phone',
  'Course Title', 'Course ID', 'Top3 Traits', 'Message'
];


// ═══════════════════════════════════════════════════════════════════════════
//  doGet — for browser testing: GET the URL to see if script is alive
// ═══════════════════════════════════════════════════════════════════════════
function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({
      status: 'ok',
      message: 'JAIN RIASEC Apps Script is running',
      timestamp: new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
}


// ═══════════════════════════════════════════════════════════════════════════
//  doPost — main handler called by Flask app
//
//  Expected payloads:
//
//  1. Save survey result (default):
//     { "row": [ts, name, email, phone, R, I, A, S, E, C, top3codes, top3names] }
//
//  2. Save enrollment:
//     { "row": [ts, name, email, phone, course, courseId, traits, message],
//       "sheet": "Enrollments" }
// ═══════════════════════════════════════════════════════════════════════════
function doPost(e) {
  // ── CORS headers so browser-side fetch() works too ──
  var output = ContentService.createTextOutput();
  output.setMimeType(ContentService.MimeType.JSON);

  try {
    // Parse the POST body
    var body = {};
    if (e && e.postData && e.postData.contents) {
      body = JSON.parse(e.postData.contents);
    } else if (e && e.parameter) {
      // fallback: form-encoded params
      body = e.parameter;
    }

    var targetSheet = body.sheet || RESULTS_SHEET;
    var row         = body.row   || [];

    if (!row || row.length === 0) {
      output.setContent(JSON.stringify({ success: false, error: 'No row data provided' }));
      return output;
    }

    // Get or create the target sheet
    var ss    = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(targetSheet);

    if (!sheet) {
      // Create sheet with headers
      sheet = ss.insertSheet(targetSheet);
      var headers = (targetSheet === ENROLLMENT_SHEET)
        ? ENROLLMENT_HEADERS
        : RESULTS_HEADERS;
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
      sheet.getRange(1, 1, 1, headers.length)
        .setBackground('#1a1a2e')
        .setFontColor('#ffffff')
        .setFontWeight('bold');
      sheet.setFrozenRows(1);
    }

    // Ensure headers exist on Sheet1 if it's empty
    if (targetSheet === RESULTS_SHEET && sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, RESULTS_HEADERS.length).setValues([RESULTS_HEADERS]);
      sheet.getRange(1, 1, 1, RESULTS_HEADERS.length)
        .setBackground('#1a1a2e')
        .setFontColor('#ffffff')
        .setFontWeight('bold');
      sheet.setFrozenRows(1);
    }

    // Append the row
    sheet.appendRow(row);

    // Auto-resize columns for readability
    try { sheet.autoResizeColumns(1, row.length); } catch(ignored) {}

    output.setContent(JSON.stringify({
      success: true,
      sheet:   targetSheet,
      rowNum:  sheet.getLastRow()
    }));

  } catch (err) {
    output.setContent(JSON.stringify({
      success: false,
      error:   err.message || String(err)
    }));
  }

  return output;
}


// ═══════════════════════════════════════════════════════════════════════════
//  Helper — called manually to set up both sheets at once
//  Run this ONCE from Apps Script editor: Run → setupSheets
// ═══════════════════════════════════════════════════════════════════════════
function setupSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  // ── Sheet1 (survey results) ──
  var s1 = ss.getSheetByName(RESULTS_SHEET);
  if (!s1) {
    s1 = ss.insertSheet(RESULTS_SHEET);
  }
  if (s1.getLastRow() === 0) {
    s1.getRange(1, 1, 1, RESULTS_HEADERS.length).setValues([RESULTS_HEADERS]);
  }
  s1.getRange(1, 1, 1, RESULTS_HEADERS.length)
    .setBackground('#1a1a2e')
    .setFontColor('#ffffff')
    .setFontWeight('bold')
    .setFontSize(11);
  s1.setFrozenRows(1);
  s1.setColumnWidth(1, 160);  // Timestamp
  s1.setColumnWidth(2, 160);  // Name
  s1.setColumnWidth(3, 220);  // Email

  // ── Enrollments ──
  var s2 = ss.getSheetByName(ENROLLMENT_SHEET);
  if (!s2) {
    s2 = ss.insertSheet(ENROLLMENT_SHEET);
  }
  if (s2.getLastRow() === 0) {
    s2.getRange(1, 1, 1, ENROLLMENT_HEADERS.length).setValues([ENROLLMENT_HEADERS]);
  }
  s2.getRange(1, 1, 1, ENROLLMENT_HEADERS.length)
    .setBackground('#0f3460')
    .setFontColor('#ffffff')
    .setFontWeight('bold')
    .setFontSize(11);
  s2.setFrozenRows(1);
  s2.setColumnWidth(1, 160);
  s2.setColumnWidth(2, 160);
  s2.setColumnWidth(3, 220);
  s2.setColumnWidth(5, 280);  // Course Title

  SpreadsheetApp.flush();
  Logger.log('✅ Sheets set up successfully');
  return 'Done';
}


// ═══════════════════════════════════════════════════════════════════════════
//  testPost — run this from Apps Script editor to test without Flask
//  Run → testPost
// ═══════════════════════════════════════════════════════════════════════════
function testPost() {
  var fakeEvent = {
    postData: {
      contents: JSON.stringify({
        row: [
          new Date().toISOString(),
          'Test Student',
          'test@example.com',
          '+911234567890',
          5, 3, 6, 4, 2, 1,
          'A, I, S',
          'Artistic, Investigative, Social'
        ]
      })
    }
  };
  var result = doPost(fakeEvent);
  Logger.log('testPost result: ' + result.getContent());
}
