// Keep the current section when switching languages. Native links still work
// without JavaScript or when analytics is unavailable.
const languageLink = document.querySelector('.language');
if (languageLink) {
  const updateLanguageLink = () => {
    const url = new URL(languageLink.href);
    url.hash = window.location.hash;
    languageLink.href = url.href;
  };
  updateLanguageLink();
  window.addEventListener('hashchange', updateLanguageLink);
  languageLink.addEventListener('click', updateLanguageLink);
}
