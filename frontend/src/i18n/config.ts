"use client";

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

import esMX from "./locales/es-MX/common.json";
import en from "./locales/en/common.json";

export const resources = {
  "es-MX": { common: esMX },
  en: { common: en },
} as const;

export const supportedLngs = ["es-MX", "en"] as const;

if (!i18n.isInitialized) {
  void i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources,
      fallbackLng: "es-MX",
      supportedLngs: [...supportedLngs],
      defaultNS: "common",
      ns: ["common"],
      interpolation: { escapeValue: false },
    });
}

export default i18n;
