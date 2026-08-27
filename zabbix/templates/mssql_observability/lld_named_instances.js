var parsed;
try {
  parsed = JSON.parse(value);
} catch (e) {
  throw 'MSSQL named-instance LLD: invalid WMI JSON';
}
var rows = [];
if (parsed === null) {
  return '[]';
}
if (Object.prototype.toString.call(parsed) === '[object Array]') {
  rows = parsed;
} else if (typeof parsed === 'object') {
  rows = [parsed];
} else {
  return '[]';
}
var PREFIX = 'MSSQL$';
var parentMacro = '{$MSSQL.PARENT.HOST}';
var out = [];
function trimCopy(text) {
  return String(text).replace(/^[ \t]+|[ \t]+$/g, '');
}
function sanitizeParent(name) {
  var cleaned = '';
  var i;
  for (i = 0; i < name.length; i++) {
    var ch = name.charAt(i);
    if (
      (ch >= '0' && ch <= '9') ||
      (ch >= 'A' && ch <= 'Z') ||
      (ch >= 'a' && ch <= 'z') ||
      ch === '_' ||
      ch === '.' ||
      ch === ' ' ||
      ch === '-'
    ) {
      cleaned += ch;
    } else {
      cleaned += '_';
    }
  }
  return trimCopy(cleaned);
}
function resolveParent(row) {
  var macro = trimCopy(parentMacro);
  var raw = '';
  if (macro && macro.indexOf('{$') !== 0 && macro !== 'CHANGE_IF_NEEDED') {
    raw = macro;
  } else if (row && typeof row.SystemName === 'string') {
    raw = row.SystemName;
  }
  return sanitizeParent(raw);
}
for (var i = 0; i < rows.length; i++) {
  var row = rows[i];
  var name = row && row.Name;
  if (typeof name !== 'string') {
    continue;
  }
  if (name.indexOf(PREFIX) !== 0) {
    continue;
  }
  if (name.indexOf('MSSQLFDLauncher') === 0) {
    continue;
  }
  var instance = name.substring(PREFIX.length);
  if (!instance) {
    continue;
  }
  var parent = resolveParent(row);
  if (!parent) {
    throw 'MSSQL named-instance LLD: missing parent host name';
  }
  out.push({
    '{#MSSQL.SERVICE}': name,
    '{#MSSQL.INSTANCE}': instance,
    '{#MSSQL.URI}': 'sqlserver://localhost/' + instance,
    '{#MSSQL.DISPLAY}': row.DisplayName || name,
    '{#MSSQL.PARENT}': parent
  });
}
return JSON.stringify(out);
