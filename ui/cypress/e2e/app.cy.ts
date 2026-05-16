describe("Membra Money Protocol E2E", () => {
  beforeEach(() => {
    cy.visit("http://localhost:5173");
  });

  it("displays devnet banner", () => {
    cy.get(".banner").should("contain", "DEVNET");
  });

  it("shows connect wallet button", () => {
    cy.get("button").contains("Connect").should("be.visible");
  });

  it("connects wallet", () => {
    cy.get("button").contains("Connect").click();
    cy.get(".wallet-connected").should("be.visible");
  });

  it("displays risk disclosure", () => {
    cy.get(".risk-disclosure").should("be.visible");
  });

  it("shows health check after connect", () => {
    cy.get("button").contains("Connect").click();
    cy.request("GET", "http://localhost:8000/health").its("body.status").should("eq", "healthy");
  });
});
