var payload;
try {
  payload = JSON.parse(value);
} catch (error) {
  throw 'XIQ-SE engine LLD: invalid health JSON';
}
var engines = payload && Array.isArray(payload.engines) ? payload.engines : [];
return JSON.stringify(enginesToLld(engines));
