import React from 'react';
import { useTranslation } from 'react-i18next';

const LanguageSelector = () => {
  const { i18n, t } = useTranslation();

  const handleLanguageChange = (e) => {
    const newLang = e.target.value;
    i18n.changeLanguage(newLang);
    localStorage.setItem('language', newLang);
    
    // Fix RTL/LTR direction switch
    if (newLang === 'ar') {
      document.documentElement.dir = 'rtl';
      document.documentElement.lang = 'ar';
    } else {
      document.documentElement.dir = 'ltr';
      document.documentElement.lang = newLang;
    }
    
    // Reload to apply layout changes
    window.location.reload();
  };

  React.useEffect(() => {
    if (i18n.language === 'ar') {
      document.documentElement.dir = 'rtl';
      document.documentElement.lang = 'ar';
    } else {
      document.documentElement.dir = 'ltr';
      document.documentElement.lang = i18n.language;
    }
  }, [i18n.language]);

  return (
    <select 
      className="language-selector" 
      value={i18n.language} 
      onChange={handleLanguageChange}
    >
      <option value="en">{t('languages.en')}</option>
      <option value="ar">{t('languages.ar')}</option>
      <option value="fr">{t('languages.fr')}</option>
    </select>
  );
};

export default LanguageSelector;