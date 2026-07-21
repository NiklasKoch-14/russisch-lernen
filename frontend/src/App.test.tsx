import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";

vi.mock("./ChatView", () => ({ default: () => <div>ChatView</div> }));
vi.mock("./VocabView", () => ({ default: () => <div>VocabView</div> }));
vi.mock("./ProfileView", () => ({ default: () => <div>ProfileView</div> }));

describe("App", () => {
  it("shows the chat view by default and switches tabs", () => {
    render(<App />);
    expect(screen.getByText("ChatView")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Vokabeln"));
    expect(screen.getByText("VocabView")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Profil"));
    expect(screen.getByText("ProfileView")).toBeInTheDocument();
  });
});
