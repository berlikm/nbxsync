var parsed;
try {
  parsed = JSON.parse(value);
} catch (e) {
  throw 'MSSQL named backup inventory: invalid last.backup.get JSON';
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
  throw 'MSSQL named backup inventory: last.backup.get must return an array';
}

var recoveryModels = {
  '1': 'FULL',
  '2': 'BULK_LOGGED',
  '3': 'SIMPLE'
};
var backupKinds = {
  D: 'full',
  I: 'diff',
  L: 'log'
};
var byName = {};

function seconds(value) {
  if (value === null || typeof value === 'undefined' || value === '') {
    return null;
  }
  var numeric = Number(value);
  return isFinite(numeric) && numeric >= 0 ? numeric : null;
}

for (var i = 0; i < rows.length; i++) {
  var row = rows[i];
  var name = row && row.dbname;
  var kind = row && backupKinds[row.type];
  if (typeof name !== 'string' || !name || !kind) {
    continue;
  }

  var record = byName[name];
  if (!record) {
    record = {name: name};
    var model = row.db_recovery_model;
    if (model !== null && typeof model !== 'undefined' && model !== '') {
      record.recovery_model = recoveryModels[String(model)] || String(model);
    }
    byName[name] = record;
  }

  var age = seconds(row.time_since_last_backup);
  if (age !== null) {
    record[kind + '_age_seconds'] = age;
  }
}

var out = [];
for (var dbname in byName) {
  if (Object.prototype.hasOwnProperty.call(byName, dbname)) {
    out.push(byName[dbname]);
  }
}
out.sort(function (a, b) {
  return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
});
return JSON.stringify(out);
