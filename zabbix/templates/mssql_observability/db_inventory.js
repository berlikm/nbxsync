var parsed;
try {
  parsed = JSON.parse(value);
} catch (e) {
  throw 'MSSQL named database inventory: invalid db.get JSON';
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
  throw 'MSSQL named database inventory: db.get must return an array';
}

var recoveryModels = {
  '1': 'FULL',
  '2': 'BULK_LOGGED',
  '3': 'SIMPLE'
};
var seen = {};
var out = [];

for (var i = 0; i < rows.length; i++) {
  var row = rows[i];
  var name = row && row.dbname;
  if (typeof name !== 'string' || !name || seen[name]) {
    continue;
  }

  seen[name] = true;
  var model = row.recovery_model;
  if (model === null || typeof model === 'undefined' || model === '') {
    model = '';
  } else {
    model = recoveryModels[String(model)] || String(model);
  }

  out.push({
    name: name,
    recovery_model: model
  });
}

out.sort(function (a, b) {
  return a.name.toLowerCase().localeCompare(b.name.toLowerCase());
});
return JSON.stringify(out);
