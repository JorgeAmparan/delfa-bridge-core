"use client";

import { useTranslation } from "react-i18next";

import "@/i18n/config";
import { Button } from "@/components/ui/button";

export default function Home() {
  const { t } = useTranslation("common");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-3xl font-semibold tracking-tight" data-testid="boot-status">
        {t("boot.status")}
      </h1>
      <p className="text-sm text-foreground/70">{t("boot.tagline")}</p>
      <Button variant="outline" size="sm">
        {t("boot.product")}
      </Button>
    </main>
  );
}
