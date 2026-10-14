// Чистая логика поиска: не обращается к DOM и не зависит от браузерного состояния.
export function normalize(text) {
  return String(text ?? '')
    .toLowerCase()
    .replace(/ё/g, 'е')
    .replace(/[^\p{L}\p{N}_–\-+]+/gu, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

const wordsOf = text => normalize(text).split(' ').filter(Boolean);

export function parseQuery(raw) {
  const include = [];
  const exclude = [];
  // Пунктуация разделяет слова и без пробелов: «творог,сыр».
  // Минус исключает термин только в начале токена: «творог -сыр»/«творог,-сыр».
  // Поэтому дефис внутри «молоко-растительное» не превращает вторую часть в исключение.
  const tokenPattern = /(?:^|[\s,;|/])-(?<negative>[\p{L}\p{N}_][\p{L}\p{N}_–\-+%]*)|(?<positive>[\p{L}\p{N}_][\p{L}\p{N}_–\-+%]*)/gu;
  for (const match of String(raw ?? '').matchAll(tokenPattern)) {
    const negative = match.groups.negative !== undefined;
    const token = negative ? match.groups.negative : match.groups.positive;
    const terms = wordsOf(token);
    (negative ? exclude : include).push(...terms);
  }
  return {
    include: [...new Set(include)],
    exclude: [...new Set(exclude)],
  };
}

const hasPrefix = (words, term) => Array.from(words).some(word => word.startsWith(term));

export function buildSearcher(index) {
  const docs = index.days.map(day => ({
    day,
    words: new Set(wordsOf(day.search ?? '')),
    meals: (day.meals ?? []).map(meal => ({
      type: meal.t,
      dish: meal.d ?? null,
      dishName: meal.dn ?? meal.d ?? null,
      dishWords: wordsOf(meal.d ?? ''),
      ingredients: (meal.i ?? []).map(ingredient => {
        if (typeof ingredient === 'string') {
          return { name: ingredient, words: wordsOf(ingredient) };
        }
        return { name: ingredient.n ?? ingredient.s, words: wordsOf(ingredient.s ?? ingredient.n ?? '') };
      }),
    })),
  }));

  return function search(raw) {
    const { include, exclude } = parseQuery(raw);
    if (!include.length && !exclude.length) return null;
    const results = [];

    for (const doc of docs) {
      if (!include.every(term => hasPrefix(doc.words, term))) continue;
      if (exclude.some(term => hasPrefix(doc.words, term))) continue;

      let score = 0;
      const hits = [];
      const mealsWithTerms = [];
      for (const meal of doc.meals) {
        let dishMatched = false;
        const ingredients = new Map();
        const matchedTerms = new Set();
        for (const term of include) {
          if (hasPrefix(meal.dishWords, term)) {
            dishMatched = true;
            matchedTerms.add(term);
          }
          meal.ingredients.forEach((ingredient, idx) => {
            if (!hasPrefix(ingredient.words, term)) return;
            matchedTerms.add(term);
            if (!ingredients.has(idx)) ingredients.set(idx, { name: ingredient.name, index: idx, terms: [] });
            const hit = ingredients.get(idx);
            if (!hit.terms.includes(term)) hit.terms.push(term);
          });
        }
        if (dishMatched) score += 5 * include.filter(term => hasPrefix(meal.dishWords, term)).length;
        const ingredientTerms = include.filter(term => meal.ingredients.some(ingredient => hasPrefix(ingredient.words, term)));
        score += 3 * ingredientTerms.length;
        if (matchedTerms.size) mealsWithTerms.push(matchedTerms);
        if (dishMatched || ingredients.size) {
          hits.push({
            type: meal.type,
            dish: meal.dishName,
            dishMatched,
            ingredients: [...ingredients.values()],
            terms: [...matchedTerms],
          });
        }
      }
      if (include.length && mealsWithTerms.some(terms => include.every(term => terms.has(term)))) score += 10;
      results.push({ day: doc.day, score, hits });
    }

    return results.sort((a, b) => b.score - a.score || a.day.index - b.day.index);
  };
}
