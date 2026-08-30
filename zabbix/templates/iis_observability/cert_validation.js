function parseCertPayload(raw) {
  try {
    return JSON.parse(raw);
  } catch (error) {
    throw 'IIS certificate: invalid JSON';
  }
}

function agentValidation(payload) {
  if (!payload || !payload.result || payload.result.value === undefined || payload.result.value === null) {
    return '';
  }
  return String(payload.result.value);
}

function agentValidationMessage(payload) {
  if (!payload || !payload.result || payload.result.message === undefined || payload.result.message === null) {
    return '';
  }
  return String(payload.result.message).replace(/\s+/g, ' ').replace(/^\s+|\s+$/g, '');
}

function userFacingValidation(payload, hasHost) {
  // Empty IIS host header: Agent 2 validates SNI 127.0.0.1 against a
  // real SAN list. That invalid is loopback identity, not a bad cert.
  // Do not pick a SAN from the certificate — that would be circular.
  if (String(hasHost) !== '1') {
    return 'not_evaluated_no_host_header';
  }
  return agentValidation(payload);
}

function rawValidationDisplay(payload) {
  var result = agentValidation(payload);
  var message = agentValidationMessage(payload);
  if (!result && !message) {
    return '';
  }
  if (message) {
    return 'Raw Agent 2 validation: ' + result + ' — ' + message;
  }
  return 'Raw Agent 2 validation: ' + result;
}
