import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const sourcePath =
  "/tmp/codex-remote-attachments/019f44c8-a894-7700-90e6-8376e9377de2/48A13E9B-F76E-42BA-80CA-A8AA59F727F2/1-Can-sample-data.xlsx";
const outputDir = "/Users/oxygen/work/personal/repos/Can-Tracker-Service/outputs/can_import_sample_20260709";
const outputPath = path.join(outputDir, "can-import-sample-reviewed.xlsx");

const importHeaders = [
  "FamilyCode",
  "FamilyHeadName",
  "PrimaryRMEmail",
  "PrimaryRMName",
  "FamilyRemarks",
  "MemberName",
  "CANNumber",
  "PAN",
  "DateOfBirth",
  "KYCStatus",
  "Mobile",
  "MobileStatus",
  "Email",
  "EmailStatus",
  "NomineeStatus",
  "BankName",
  "AccountNumber",
  "IFSC",
  "PayEezzStatus",
  "PayEezzAmount",
  "PayEezzStartDate",
  "Remarks",
  "ImportReviewStatus",
  "Issues",
];

const allowedKyc = new Set(["Validated", "Registered", "No KYC"]);
const allowedVerification = new Set(["Verified", "Not Verified"]);
const allowedPayeezz = new Set(["Not Available", "Sent for Approval", "Aggregator Accepted"]);
const panRegex = /^[A-Z]{5}[0-9]{4}[A-Z]$/;

function text(value) {
  if (value === null || value === undefined) return "";
  return String(value).trim();
}

function normalizedKey(value) {
  return text(value).toUpperCase().replace(/\s+/g, " ");
}

function safeSlug(value) {
  const slug = normalizedKey(value).replace(/[^A-Z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return slug || "UNKNOWN";
}

function hash6(value) {
  let hash = 0x811c9dc5;
  for (const char of value) {
    hash ^= char.charCodeAt(0);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(36).toUpperCase().padStart(6, "0").slice(0, 6);
}

function familyCode(familyHeadName) {
  const slug = safeSlug(familyHeadName).slice(0, 49).replace(/-+$/g, "");
  return `FAM-${slug}-${hash6(normalizedKey(familyHeadName))}`.slice(0, 64);
}

function toIsoDate(value) {
  if (!value) return "";
  const raw = text(value);
  if (!raw || raw.toUpperCase() === "NA") return "";
  const date = new Date(value);
  if (!Number.isNaN(date.getTime())) {
    return date.toISOString().slice(0, 10);
  }
  return raw;
}

function cleanAmount(value) {
  const raw = text(value);
  if (!raw || raw.toUpperCase() === "NA") return "";
  return raw;
}

function defaultStatus(value, fallback, allowed) {
  const raw = text(value);
  return allowed.has(raw) ? raw : fallback;
}

function duplicateKey(row) {
  const can = normalizedKey(row["CAN Number"]);
  const mobile = normalizedKey(row.Mobile);
  const number = can && can !== "NA" ? `CAN:${can}` : mobile ? `MOBILE:${mobile}` : "";
  return [normalizedKey(row["Family Head"]), normalizedKey(row.Name), number].join("|");
}

function rowObject(headers, values) {
  const result = {};
  headers.forEach((header, index) => {
    result[header] = values[index] ?? "";
  });
  return result;
}

function cellAddress(rowNumber, colNumber) {
  let column = "";
  let number = colNumber;
  while (number > 0) {
    const remainder = (number - 1) % 26;
    column = String.fromCharCode(65 + remainder) + column;
    number = Math.floor((number - 1) / 26);
  }
  return `${column}${rowNumber}`;
}

function applyBaseSheetStyle(sheet, rowCount, colCount) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format.fill.color = "#1F4E78";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.wrapText = true;
  header.format.rowHeightPx = 34;
  const used = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  used.format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
  used.format.font.name = "Arial";
  used.format.font.size = 10;
  used.format.autofitColumns();
}

const input = await FileBlob.load(sourcePath);
const sourceWorkbook = await SpreadsheetFile.importXlsx(input);
const sourceSheet = sourceWorkbook.worksheets.getItemAt(0);
const usedRange = sourceSheet.getUsedRange(true);
const sourceValues = usedRange.values;
const rawHeaders = sourceValues[0].map(text);
const rawRows = sourceValues
  .slice(1)
  .filter((row) => row.some((cell) => text(cell) !== ""))
  .map((row, index) => ({ sourceRow: index + 2, raw: rowObject(rawHeaders, row) }));

const seen = new Map();
let generatedCanCount = 0;
const transformed = [];

for (const item of rawRows) {
  const key = duplicateKey(item.raw);
  const isDuplicate = seen.has(key);
  if (!isDuplicate) seen.set(key, item.sourceRow);

  const familyHeadName = text(item.raw["Family Head"]);
  const memberName = text(item.raw.Name);
  const rawCan = text(item.raw["CAN Number"]);
  let canNumber = rawCan && rawCan.toUpperCase() !== "NA" ? rawCan.toUpperCase() : "";
  const issues = [];
  const notes = [];
  const redHeaders = new Set();

  if (!familyHeadName) {
    issues.push("FamilyHeadName missing");
    redHeaders.add("FamilyHeadName");
    redHeaders.add("FamilyCode");
  }
  if (!memberName) {
    issues.push("MemberName missing");
    redHeaders.add("MemberName");
  }
  if (!canNumber) {
    generatedCanCount += 1;
    canNumber = `CAN-PENDING-${String(item.sourceRow).padStart(6, "0")}`;
    notes.push("CANNumber generated as CAN-PENDING placeholder; replace with real MFU CAN when available");
  }
  if (isDuplicate) {
    issues.push(`Possible duplicate of source row ${seen.get(key)}`);
    redHeaders.add("CANNumber");
    redHeaders.add("MemberName");
    redHeaders.add("FamilyHeadName");
  }

  const pan = normalizedKey(item.raw.PAN);
  if (pan && pan !== "NA" && !panRegex.test(pan)) {
    issues.push("PAN format invalid");
    redHeaders.add("PAN");
  }

  const payeezzStartDate = toIsoDate(item.raw["Payeezz Start Date"]);
  if (payeezzStartDate && !/^\d{4}-\d{2}-\d{2}$/.test(payeezzStartDate)) {
    issues.push("PayEezzStartDate must be YYYY-MM-DD");
    redHeaders.add("PayEezzStartDate");
  }

  const amount = cleanAmount(item.raw["Payeezz Amount"]);
  if (amount && Number.isNaN(Number(amount))) {
    issues.push("PayEezzAmount must be numeric");
    redHeaders.add("PayEezzAmount");
  }

  const sourceKyc = text(item.raw["KYC Status"]);
  const sourceMobileStatus = text(item.raw["Mobile Status"]);
  const sourceEmailStatus = text(item.raw["Email Status"]);
  const sourceNomineeStatus = text(item.raw["Nominee Status"]);
  const sourcePayeezzStatus = text(item.raw["Payeezz Status"]);

  if (!allowedKyc.has(sourceKyc)) {
    notes.push(`KYCStatus defaulted from "${sourceKyc || "blank"}" to "No KYC"`);
  }
  if (!allowedVerification.has(sourceMobileStatus)) {
    notes.push(`MobileStatus defaulted from "${sourceMobileStatus || "blank"}" to "Not Verified"`);
  }
  if (!allowedVerification.has(sourceEmailStatus)) {
    notes.push(`EmailStatus defaulted from "${sourceEmailStatus || "blank"}" to "Not Verified"`);
  }
  if (!allowedVerification.has(sourceNomineeStatus)) {
    notes.push(`NomineeStatus defaulted from "${sourceNomineeStatus || "blank"}" to "Not Verified"`);
  }
  if (!allowedPayeezz.has(sourcePayeezzStatus)) {
    notes.push(`PayEezzStatus defaulted from "${sourcePayeezzStatus || "blank"}" to "Not Available"`);
  }

  const row = {
    FamilyCode: familyHeadName ? familyCode(familyHeadName) : "",
    FamilyHeadName: familyHeadName,
    PrimaryRMEmail: "",
    PrimaryRMName: "",
    FamilyRemarks: "",
    MemberName: memberName,
    CANNumber: canNumber,
    PAN: pan === "NA" ? "" : pan,
    DateOfBirth: "",
    KYCStatus: defaultStatus(sourceKyc, "No KYC", allowedKyc),
    Mobile: text(item.raw.Mobile).toUpperCase() === "NA" ? "" : text(item.raw.Mobile),
    MobileStatus: defaultStatus(sourceMobileStatus, "Not Verified", allowedVerification),
    Email: text(item.raw.Email).toUpperCase() === "NA" ? "" : text(item.raw.Email).toLowerCase(),
    EmailStatus: defaultStatus(sourceEmailStatus, "Not Verified", allowedVerification),
    NomineeStatus: defaultStatus(sourceNomineeStatus, "Not Verified", allowedVerification),
    BankName: text(item.raw["Bank Name"]).toUpperCase() === "NA" ? "" : text(item.raw["Bank Name"]),
    AccountNumber: text(item.raw["Bank Account"]).toUpperCase() === "NA" ? "" : text(item.raw["Bank Account"]),
    IFSC: "",
    PayEezzStatus: defaultStatus(sourcePayeezzStatus, "Not Available", allowedPayeezz),
    PayEezzAmount: amount,
    PayEezzStartDate: payeezzStartDate,
    Remarks:
      issues.length || notes.length
        ? `Source row ${item.sourceRow}: ${[...issues, ...notes].join("; ")}`
        : `Source row ${item.sourceRow}`,
    ImportReviewStatus: issues.length ? "Needs review" : "Ready",
    Issues: issues.join("; "),
  };
  transformed.push({ row, redHeaders, sourceRow: item.sourceRow });
}

const workbook = Workbook.create();
const importSheet = workbook.worksheets.add("Import");
const rawSheet = workbook.worksheets.add("RawData");
const lookupSheet = workbook.worksheets.add("Lookups");

const importMatrix = [importHeaders, ...transformed.map(({ row }) => importHeaders.map((header) => row[header] ?? ""))];
importSheet.getRangeByIndexes(0, 0, importMatrix.length, importHeaders.length).values = importMatrix;
applyBaseSheetStyle(importSheet, importMatrix.length, importHeaders.length);
importSheet.freezePanes.freezeColumns(2);
importSheet.getRangeByIndexes(1, 0, importMatrix.length - 1, importHeaders.length).format.wrapText = true;
importSheet.getRangeByIndexes(1, 19, importMatrix.length - 1, 1).format.numberFormat = [["0.00"]];
importSheet.getRangeByIndexes(1, 20, importMatrix.length - 1, 1).format.numberFormat = [["yyyy-mm-dd"]];
importSheet.getRangeByIndexes(1, 22, importMatrix.length - 1, 2).format.fill.color = "#FFF2CC";

const redFill = "#F4CCCC";
const redFont = "#9C0006";
const headerIndex = new Map(importHeaders.map((header, index) => [header, index]));
for (let i = 0; i < transformed.length; i += 1) {
  const excelRow = i + 2;
  for (const header of transformed[i].redHeaders) {
    const columnIndex = headerIndex.get(header);
    if (columnIndex === undefined) continue;
    const cell = importSheet.getRange(cellAddress(excelRow, columnIndex + 1));
    cell.format.fill.color = redFill;
    cell.format.font.color = redFont;
  }
  const primaryRmEmailCell = importSheet.getRange(cellAddress(excelRow, headerIndex.get("PrimaryRMEmail") + 1));
  primaryRmEmailCell.format.fill.color = redFill;
  primaryRmEmailCell.format.font.color = redFont;
}

const statusRange = importSheet.getRangeByIndexes(1, 22, transformed.length, 1);
statusRange.conditionalFormats.add("containsText", {
  text: "Needs review",
  format: { fill: { color: "#FCE4D6" }, font: { color: "#C00000", bold: true } },
});
statusRange.conditionalFormats.add("containsText", {
  text: "Ready",
  format: { fill: { color: "#E2F0D9" }, font: { color: "#375623", bold: true } },
});

importSheet.getRangeByIndexes(1, headerIndex.get("KYCStatus"), transformed.length, 1).dataValidation = {
  rule: { type: "list", values: ["Validated", "Registered", "No KYC"] },
};
for (const header of ["MobileStatus", "EmailStatus", "NomineeStatus"]) {
  importSheet.getRangeByIndexes(1, headerIndex.get(header), transformed.length, 1).dataValidation = {
    rule: { type: "list", values: ["Verified", "Not Verified"] },
  };
}
importSheet.getRangeByIndexes(1, headerIndex.get("PayEezzStatus"), transformed.length, 1).dataValidation = {
  rule: { type: "list", values: ["Not Available", "Sent for Approval", "Aggregator Accepted"] },
};

const rawMatrix = [["SourceRow", ...rawHeaders], ...rawRows.map(({ sourceRow, raw }) => [sourceRow, ...rawHeaders.map((header) => raw[header] ?? "")])];
rawSheet.getRangeByIndexes(0, 0, rawMatrix.length, rawMatrix[0].length).values = rawMatrix;
applyBaseSheetStyle(rawSheet, rawMatrix.length, rawMatrix[0].length);
rawSheet.freezePanes.freezeColumns(1);

const lookupRows = [
  ["Field", "Allowed values / guidance"],
  ["KYCStatus", "Validated | Registered | No KYC"],
  ["MobileStatus", "Verified | Not Verified"],
  ["EmailStatus", "Verified | Not Verified"],
  ["NomineeStatus", "Verified | Not Verified"],
  ["PayEezzStatus", "Not Available | Sent for Approval | Aggregator Accepted"],
  ["PrimaryRMEmail", "Required before upload; must match one active RM user in the app."],
  ["FamilyCode", "Generated from FamilyHeadName. Keep stable once uploaded."],
  ["CANNumber", "Blank/NA values are generated as CAN-PENDING placeholders; replace with real MFU CAN numbers when available."],
  ["Red cells", "Required/manual review before clean upload."],
  ["Yellow columns", "Review-only helper columns; remove before uploading if exporting a strict service template."],
];
lookupSheet.getRangeByIndexes(0, 0, lookupRows.length, 2).values = lookupRows;
applyBaseSheetStyle(lookupSheet, lookupRows.length, 2);
lookupSheet.getRange("A1:B1").format.fill.color = "#548235";
lookupSheet.getRange("A2:B11").format.wrapText = true;

const summaryRows = [
  ["Metric", "Count"],
  ["Source populated rows", rawRows.length],
  ["Rows in Import sheet", transformed.length],
  ["Rows marked Needs review", transformed.filter(({ row }) => row.ImportReviewStatus === "Needs review").length],
  ["Rows marked Ready", transformed.filter(({ row }) => row.ImportReviewStatus === "Ready").length],
  ["CAN-PENDING placeholders generated", generatedCanCount],
];
lookupSheet.getRange("D1:E6").values = summaryRows;
lookupSheet.getRange("D1:E1").format.fill.color = "#1F4E78";
lookupSheet.getRange("D1:E1").format.font.color = "#FFFFFF";
lookupSheet.getRange("D1:E1").format.font.bold = true;
lookupSheet.getRange("D1:E6").format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
lookupSheet.getRange("D2:E6").format.fill.color = "#EAF2F8";
lookupSheet.getRange("D1:E6").format.autofitColumns();

await fs.mkdir(outputDir, { recursive: true });
const exported = await SpreadsheetFile.exportXlsx(workbook);
await exported.save(outputPath);

const preview = await workbook.render({ sheetName: "Import", range: "A1:X18", scale: 1, format: "png" });
const previewBytes = new Uint8Array(await preview.arrayBuffer());
await fs.writeFile(path.join(outputDir, "import-preview.png"), previewBytes);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "formula error scan",
});
console.log(errors.ndjson);
console.log(outputPath);
