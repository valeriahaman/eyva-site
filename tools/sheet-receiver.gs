// EYVA waitlist — Google Sheet receiver.
// Lives in the Apps Script attached to the sheet "EYVA waitlist". The site posts one row per signup.
// Also sends Val a short daily summary at 09:00 (Dubai) once setup() has been run once.

var TOKEN = "eyva-2026-sheet";          // must match SHEET_TOKEN on the site
var SUMMARY_TO = "val@eyva.me";

function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  if (data.token !== TOKEN) {
    return ContentService.createTextOutput("no").setMimeType(ContentService.MimeType.TEXT);
  }
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  sheet.appendRow(data.row);
  return ContentService.createTextOutput("ok").setMimeType(ContentService.MimeType.TEXT);
}

// Run once by hand: creates the daily summary trigger.
function setup() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger("dailySummary").timeBased().everyDays(1).atHour(9).inTimezone("Asia/Dubai").create();
}

function dailySummary() {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  var rows = sheet.getDataRange().getValues().slice(1);
  var since = new Date(Date.now() - 24 * 3600 * 1000);
  var total = 0, today = 0, colours = {};
  rows.forEach(function (r) {
    if (r[1] !== "join") return;
    total++;
    if (new Date(r[0]) > since) today++;
    var c = r[4] || "no colour"; colours[c] = (colours[c] || 0) + 1;
  });
  var lines = ["Waitlist: " + total + " in total, " + today + " in the last 24 hours.", ""];
  Object.keys(colours).forEach(function (c) { lines.push(c + ": " + colours[c]); });
  lines.push("", SpreadsheetApp.getActiveSpreadsheet().getUrl());
  MailApp.sendEmail(SUMMARY_TO, "EYVA waitlist — " + total + " (+" + today + ")", lines.join("\n"));
}
