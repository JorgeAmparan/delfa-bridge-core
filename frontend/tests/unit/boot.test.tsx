import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

// Importa un componente shadcn/ui para verificar que el toolchain (TSX + Tailwind
// variants + Radix Slot + alias @/) compila y renderiza.
import { Button } from "@/components/ui/button";

describe("toolchain boot", () => {
  it("renders a shadcn/ui Button", () => {
    render(<Button>DOCYAN — boot OK</Button>);
    const btn = screen.getByRole("button", { name: "DOCYAN — boot OK" });
    expect(btn).toBeInTheDocument();
  });

  it("applies cva variant classes", () => {
    render(<Button variant="outline">outline</Button>);
    const btn = screen.getByRole("button", { name: "outline" });
    expect(btn.className).toContain("border");
  });
});
