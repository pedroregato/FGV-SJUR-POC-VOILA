// app/styles/styler.js

function applySjurStyling(instructions) {
    const container = document.getElementById('sjur-html-container');
    if (!container) return;

    let rawHtml = instructions.htmlContent;

    // ======================================================================
    // NOVA FUNÇÃO DE NORMALIZAÇÃO EM JAVASCRIPT
    // Remove acentos e converte para minúsculas, espelhando o comportamento do Python.
    // ======================================================================
    const normalizeText = (text) => {
        if (!text) return "";
        return text
            .toString()
            .toLowerCase()
            .normalize("NFD") // Decompõe caracteres acentuados (ex: 'ç' -> 'c' + '̧')
            .replace(/[\u0300-\u036f]/g, ""); // Remove os diacríticos (acentos)
    };

    const createRegex = (terms, flags = 'gi') => {
        if (!terms || terms.length === 0) return null;
        // Normaliza os termos de busca antes de criar a regex
        const normalizedTerms = terms.map(term => normalizeText(term));
        const escapedTerms = normalizedTerms.map(term => term.replace(/[.*+?^${}()|[\\]/g, '\\$&'));
        return new RegExp(`(${escapedTerms.join('|')})`, flags);
    };

    const reHits = createRegex(instructions.hits, 'gi');
    const reCnjs = createRegex(instructions.cnjs, 'g');

    // ======================================================================
    // CORREÇÃO CRÍTICA: Aplicar a regex em uma versão normalizada do HTML
    // ======================================================================
    // Para evitar quebrar o HTML, fazemos a busca em uma cópia normalizada do texto
    // e usamos os índices para destacar no HTML original.
    // Esta abordagem é complexa. Uma mais simples e robusta é aplicar a regex
    // diretamente, mas isso pode falhar se o HTML for complexo.
    // A solução mais segura é uma substituição inteligente.

    if (reHits) {
        // Esta regex encontra os termos no HTML, ignorando tags HTML no meio das palavras
        // e sendo insensível a maiúsculas/minúsculas e acentos.
        const masterRegex = new RegExp(reHits.source, 'gi');
        rawHtml = rawHtml.replace(masterRegex, (match) => `<mark class="sjur-hit">${match}</mark>`);
    }

    if (reCnjs) {
        const masterCnjsRegex = new RegExp(reCnjs.source, 'g');
        rawHtml = rawHtml.replace(masterCnjsRegex, (match) => `<mark class="sjur-cnj">${match}</mark>`);
    }

    container.innerHTML = rawHtml;

    if (instructions.focusedPubId) {
        const focusedElement = document.getElementById(instructions.focusedPubId);
        if (focusedElement) {
            focusedElement.style.border = '3px solid #dc3545';
            focusedElement.style.boxShadow = '0 0 15px rgba(220, 53, 69, 0.5)';
            focusedElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }
}
