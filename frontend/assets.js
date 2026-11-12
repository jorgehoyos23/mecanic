'use strict';
/* =====================================================================
 * Mecasolic · Ilustraciones vectoriales (SVG) de productos y servicios
 * Usan los degradados globales #gNeon, #gHot y #gFill
 * definidos en index.html. Clases: .f = relleno, .h = trazo cálido.
 * ===================================================================== */

const ART = {
  // ---------------------------------------------------------- repuestos
  aceite: `
    <path class="f" d="M38 48 L50 34 H70 V46 L82 58 V98 Q82 104 76 104 H44 Q38 104 38 98 Z"/>
    <rect x="52" y="22" width="16" height="12" rx="2"/>
    <path d="M82 62 L96 54 L98 60 L84 70" />
    <rect class="h" x="46" y="64" width="28" height="26" rx="3"/>
    <path class="h" d="M60 69 q-6 8 0 13 q6 -5 0 -13z"/>`,
  filtro: `
    <path class="f" d="M32 34 V88 Q60 102 88 88 V34"/>
    <ellipse cx="60" cy="34" rx="28" ry="9"/>
    <path d="M42 41 V92 M51 42 V95 M60 43 V96 M69 42 V95 M78 41 V92" opacity=".55"/>
    <ellipse class="h" cx="60" cy="34" rx="10" ry="3.5"/>
    <path class="h" d="M32 60 Q60 72 88 60"/>`,
  filtro_aire: `
    <rect class="f" x="16" y="32" width="88" height="56" rx="8"/>
    <polyline class="h" points="26,42 31,78 36,42 41,78 46,42 51,78 56,42 61,78 66,42 71,78 76,42 81,78 86,42 91,78 94,42"/>
    <path d="M16 46 H10 M16 74 H10 M104 46 H110 M104 74 H110" opacity=".6"/>`,
  pastillas: `
    <path class="f" d="M20 66 A42 42 0 0 1 100 66 L86 72 A28 28 0 0 0 34 72 Z"/>
    <path class="f" d="M28 94 A34 34 0 0 1 92 94 L80 100 A22 22 0 0 0 40 100 Z"/>
    <path class="h" d="M24 62 A38 38 0 0 1 96 62"/>
    <circle class="h" cx="44" cy="52" r="3"/><circle class="h" cx="76" cy="52" r="3"/>`,
  disco: `
    <circle class="f" cx="60" cy="60" r="44"/>
    <circle cx="60" cy="60" r="34" opacity=".5"/>
    <circle class="h" cx="60" cy="60" r="15"/>
    <circle cx="60" cy="38" r="3"/><circle cx="81" cy="53" r="3"/><circle cx="73" cy="78" r="3"/>
    <circle cx="47" cy="78" r="3"/><circle cx="39" cy="53" r="3"/>
    <path d="M60 18 V24 M102 60 H96 M60 102 V96 M18 60 H24 M90 30 L86 34 M30 90 L34 86 M90 90 L86 86 M30 30 L34 34" opacity=".7"/>
    <path class="h" d="M92 26 A46 46 0 0 1 106 52"/>`,
  liquido: `
    <path class="f" d="M40 42 H80 V98 Q80 104 74 104 H46 Q40 104 40 98 Z"/>
    <rect x="50" y="24" width="20" height="18" rx="3"/>
    <path d="M44 56 H76" opacity=".5"/>
    <path class="h" d="M60 64 q-9 12 0 20 q9 -8 0 -20z"/>
    <text x="60" y="98" text-anchor="middle" class="t">DOT4</text>`,
  bateria: `
    <rect class="f" x="16" y="40" width="88" height="58" rx="7"/>
    <rect class="h" x="28" y="28" width="16" height="12" rx="2"/>
    <rect x="76" y="28" width="16" height="12" rx="2"/>
    <path class="h" d="M30 60 h14 M37 53 v14"/>
    <path d="M76 60 h14"/>
    <path class="h" d="M64 52 l-9 16 h11 l-7 16"/>`,
  bujia: `
    <rect x="53" y="10" width="14" height="10" rx="2"/>
    <path class="f" d="M50 20 H70 L68 50 H52 Z"/>
    <path d="M52 28 H68 M52 36 H68 M52 44 H68" opacity=".5"/>
    <path class="h" d="M42 50 H78 V64 H42 Z"/>
    <path d="M50 64 H70 V88 H50 Z"/>
    <path d="M50 70 L70 67 M50 76 L70 73 M50 82 L70 79" opacity=".7"/>
    <path class="h" d="M60 88 V98 H70 V94"/>
    <path class="h" d="M76 98 l6 -2 M76 92 l7 -5" opacity=".8"/>`,
  correa: `
    <circle class="f" cx="38" cy="70" r="22"/>
    <circle class="f" cx="88" cy="40" r="15"/>
    <circle class="h" cx="38" cy="70" r="6"/>
    <circle class="h" cx="88" cy="40" r="4"/>
    <path d="M30 46 L82 23 M47 92 L100 50"/>
    <path d="M30 46 A26 26 0 0 0 47 92 M82 23 A19 19 0 0 1 100 50" />
    <path d="M44 41 l1 4 M56 36 l1 4 M68 31 l1 4 M58 82 l-1 -4 M70 72 l-1 -4 M82 63 l-1 -4" opacity=".7"/>`,
  amortiguador: `
    <circle cx="60" cy="12" r="6"/>
    <rect x="54" y="18" width="12" height="36" rx="3"/>
    <rect class="f" x="45" y="56" width="30" height="46" rx="5"/>
    <path class="h" d="M38 26 L82 32 L38 38 L82 44 L38 50 L82 56 L38 62 L82 68 L38 74 L82 80"/>
    <circle cx="60" cy="108" r="6"/>`,
  repuesto: `
    <circle cx="60" cy="60" r="34" stroke-width="12" stroke-dasharray="9 8.8" opacity=".9"/>
    <circle class="f" cx="60" cy="60" r="26"/>
    <circle class="h" cx="60" cy="60" r="10"/>`,

  // ---------------------------------------------------------- servicios
  mantenimiento: `
    <path class="f" d="M80 18 A20 20 0 0 0 56 44 L20 80 A9 9 0 0 0 33 93 L69 57 A20 20 0 0 0 95 33 L82 44 L72 42 L70 32 Z"/>
    <circle cx="27" cy="86" r="3"/>
    <circle class="h" cx="88" cy="88" r="16"/>
    <path class="h" d="M80 88 l6 6 l10 -12"/>`,
  alineacion: `
    <circle class="f" cx="60" cy="60" r="38"/>
    <circle cx="60" cy="60" r="24"/>
    <circle class="h" cx="60" cy="60" r="7"/>
    <path d="M60 36 V53 M83 53 L67 58 M74 80 L64 66 M46 80 L56 66 M37 53 L53 58"/>
    <path class="h" d="M8 60 H18 M12 54 L18 60 L12 66 M112 60 H102 M108 54 L102 60 L108 66"/>`,
  frenos: `
    <circle class="f" cx="56" cy="64" r="38"/>
    <circle cx="56" cy="64" r="13"/>
    <circle cx="56" cy="44" r="2.5"/><circle cx="75" cy="58" r="2.5"/><circle cx="68" cy="80" r="2.5"/>
    <circle cx="44" cy="80" r="2.5"/><circle cx="37" cy="58" r="2.5"/>
    <path class="h" d="M78 22 Q104 34 106 62 L92 64 Q90 44 72 34 Z"/>`,
  motor: `
    <path class="f" d="M24 52 H40 V42 H76 V52 H92 L100 60 V86 H24 Z"/>
    <path d="M34 42 V30 H50 V42 M62 42 V30 H78" />
    <path d="M44 30 H56 V22 M72 30 V22" opacity=".6"/>
    <path d="M24 64 H12 V78 H24 M100 68 H110"/>
    <circle class="h" cx="62" cy="70" r="10"/>
    <path class="h" d="M62 60 V80 M52 70 H72"/>`,
  electrico: `
    <rect class="f" x="18" y="46" width="70" height="50" rx="7"/>
    <rect x="28" y="36" width="14" height="10" rx="2"/><rect x="64" y="36" width="14" height="10" rx="2"/>
    <path class="h" d="M98 14 L78 52 H94 L80 92"/>
    <path d="M30 70 h12 M36 64 v12 M64 70 h12"/>`,
  diagnostico: `
    <rect class="f" x="16" y="24" width="72" height="56" rx="7"/>
    <polyline class="h" points="24,58 36,58 42,44 50,70 58,38 64,58 80,58"/>
    <path d="M52 80 V90 Q52 100 64 100 H96 Q104 100 104 92 V80"/>
    <rect x="96" y="68" width="16" height="12" rx="2"/>`,
  vehiculo: `
    <path class="f" d="M10 76 L20 58 Q26 48 40 46 L64 44 Q76 44 84 52 L94 60 Q108 62 110 72 L110 82 H10 Z"/>
    <path d="M36 56 L44 50 H62 L70 58 Z M74 58 L68 50 Q76 50 82 58 Z" opacity=".75"/>
    <circle class="h" cx="34" cy="82" r="11"/><circle class="h" cx="88" cy="82" r="11"/>
    <circle cx="34" cy="82" r="4"/><circle cx="88" cy="82" r="4"/>
    <path class="h" d="M104 68 h6" />
    <path d="M2 90 H118" opacity=".35"/>`,
};

/** Devuelve el SVG de una ilustración. */
function art(key, cls = '') {
  return `<svg class="art ${cls}" viewBox="0 0 120 120" aria-hidden="true"><g class="art-g">${ART[key] || ART.repuesto}</g></svg>`;
}

function pickArt(text, rules, fallback) {
  const t = text.toLowerCase();
  const hit = rules.find(([re]) => new RegExp(re).test(t));
  return hit ? hit[1] : fallback;
}

/** Ilustración según el repuesto (SKU, nombre y categoría). */
function partArt(p) {
  return pickArt(`${p.sku} ${p.name} ${p.category}`, [
    ['aceite|lubric', 'aceite'], ['filtro de aire|fil-air', 'filtro_aire'], ['filtro', 'filtro'],
    ['pastilla', 'pastillas'], ['disco', 'disco'], ['líquido|liquido|dot', 'liquido'],
    ['bater', 'bateria'], ['bujía|bujia|encendido', 'bujia'], ['correa|distribuci', 'correa'],
    ['amortig|suspensi', 'amortiguador'], ['fren', 'pastillas'], ['eléctr|electr', 'bateria'],
  ], 'repuesto');
}

/** Ilustración según el servicio del catálogo. */
function serviceArt(s) {
  return pickArt(`${s.name || ''} ${s.category || ''}`, [
    ['aceite', 'aceite'], ['alineaci|balanceo|llanta', 'alineacion'], ['fren', 'frenos'],
    ['motor', 'motor'], ['eléctr|electr|bater', 'electrico'], ['diagn|escáner|escaner', 'diagnostico'],
  ], 'mantenimiento');
}
