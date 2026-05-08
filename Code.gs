/**
 * JAIN RIASEC — Google Apps Script
 * Handles: saving survey results, saving enrollments, reading sheet data, DELETING rows
 */

var RESULTS_SHEET    = 'Sheet1';
var ENROLLMENT_SHEET = 'Enrollments';

var RESULTS_HEADERS = [
  'Timestamp', 'Name', 'Email', 'Phone',
  'R', 'I', 'A', 'S', 'E', 'C',
  'Top3 Codes', 'Top3 Names'
];

var ENROLLMENT_HEADERS = [
  'Timestamp', 'Name', 'Email', 'Phone',
  'Course Title', 'Course ID', 'Top3 Traits', 'Message'
];


function doGet(e) {
  return ContentService
    .createTextOutput(JSON.stringify({
      status: 'ok',
      message: 'JAIN RIASEC Apps Script is running',
      timestamp: new Date().toISOString()
    }))
    .setMimeType(ContentService.MimeType.JSON);
}


function doPost(e) {
  var output = ContentService.createTextOutput();
  output.setMimeType(ContentService.MimeType.JSON);

  try {
    var body = {};
    if (e && e.postData && e.postData.contents) {
      body = JSON.parse(e.postData.contents);
    } else if (e && e.parameter) {
      body = e.parameter;
    }

    // ── HANDLE DELETE ACTION ──────────────────────────────────────────────────
    if (body.action === 'delete') {
      var rowIndex = parseInt(body.rowIndex || 0, 10);
      var sheetName = body.sheet || RESULTS_SHEET;

      if (!rowIndex || rowIndex < 2) {
        output.setContent(JSON.stringify({ success: false, error: 'Invalid row index' }));
        return output;
      }

      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sheet = ss.getSheetByName(sheetName);

      if (!sheet) {
        output.setContent(JSON.stringify({ success: false, error: 'Sheet not found: ' + sheetName }));
        return output;
      }

      var lastRow = sheet.getLastRow();
      if (rowIndex > lastRow) {
        output.setContent(JSON.stringify({ success: false, error: 'Row ' + rowIndex + ' does not exist (last row: ' + lastRow + ')' }));
        return output;
      }

      sheet.deleteRow(rowIndex);
      SpreadsheetApp.flush();

      output.setContent(JSON.stringify({
        success: true,
        deleted: rowIndex,
        sheet: sheetName
      }));
      return output;
    }

    // ── HANDLE APPEND (default) ───────────────────────────────────────────────
    var targetSheet = body.sheet || RESULTS_SHEET;
    var row         = body.row   || [];

    if (!row || row.length === 0) {
      output.setContent(JSON.stringify({ success: false, error: 'No row data provided' }));
      return output;
    }

    var ss    = SpreadsheetApp.getActiveSpreadsheet();
    var sheet = ss.getSheetByName(targetSheet);

    if (!sheet) {
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

    if (targetSheet === RESULTS_SHEET && sheet.getLastRow() === 0) {
      sheet.getRange(1, 1, 1, RESULTS_HEADERS.length).setValues([RESULTS_HEADERS]);
      sheet.getRange(1, 1, 1, RESULTS_HEADERS.length)
        .setBackground('#1a1a2e')
        .setFontColor('#ffffff')
        .setFontWeight('bold');
      sheet.setFrozenRows(1);
    }

    sheet.appendRow(row);
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


function setupSheets() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();

  var s1 = ss.getSheetByName(RESULTS_SHEET);
  if (!s1) { s1 = ss.insertSheet(RESULTS_SHEET); }
  if (s1.getLastRow() === 0) {
    s1.getRange(1, 1, 1, RESULTS_HEADERS.length).setValues([RESULTS_HEADERS]);
  }
  s1.getRange(1, 1, 1, RESULTS_HEADERS.length)
    .setBackground('#1a1a2e').setFontColor('#ffffff').setFontWeight('bold').setFontSize(11);
  s1.setFrozenRows(1);
  s1.setColumnWidth(1, 160);
  s1.setColumnWidth(2, 160);
  s1.setColumnWidth(3, 220);

  var s2 = ss.getSheetByName(ENROLLMENT_SHEET);
  if (!s2) { s2 = ss.insertSheet(ENROLLMENT_SHEET); }
  if (s2.getLastRow() === 0) {
    s2.getRange(1, 1, 1, ENROLLMENT_HEADERS.length).setValues([ENROLLMENT_HEADERS]);
  }
  s2.getRange(1, 1, 1, ENROLLMENT_HEADERS.length)
    .setBackground('#0f3460').setFontColor('#ffffff').setFontWeight('bold').setFontSize(11);
  s2.setFrozenRows(1);
  s2.setColumnWidth(1, 160);
  s2.setColumnWidth(2, 160);
  s2.setColumnWidth(3, 220);
  s2.setColumnWidth(5, 280);

  SpreadsheetApp.flush();
  Logger.log('✅ Sheets set up successfully');
  return 'Done';
}


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

function testDelete() {
  var fakeEvent = {
    postData: {
      contents: JSON.stringify({
        action: 'delete',
        rowIndex: 3,
        sheet: 'Sheet1'
      })
    }
  };
  var result = doPost(fakeEvent);
  Logger.log('testDelete result: ' + result.getContent());
}
