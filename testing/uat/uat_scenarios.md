# UAT Scenarios

## Scope

These scenarios validate end-user workflows after deployment. They are manual acceptance tests and should be run in a staging environment.

## Test Data

- Admin account: approved and active
- Researcher account: approved and active
- User account: approved and active
- Demo symbol: BTC-USD

## Scenario Matrix

| ID     | Role       | Scenario                          | Expected Result                                             | Evidence                   |
| ------ | ---------- | --------------------------------- | ----------------------------------------------------------- | -------------------------- |
| UAT-01 | User       | Login with valid email/password   | Session token is created and dashboard loads                | Screenshot + API response  |
| UAT-02 | User       | Request prediction for BTC-USD    | Prediction response includes trend, confidence, explanation | Screenshot + payload       |
| UAT-03 | User       | Create price alert (target above) | Alert appears in alert list with enabled status             | Screenshot                 |
| UAT-04 | User       | Manage portfolio holding          | Holding is created/updated and PnL values refresh           | Screenshot                 |
| UAT-05 | Researcher | Fetch historical data             | Data fetch endpoint succeeds and data rows increase         | API logs + screenshot      |
| UAT-06 | Researcher | Train models                      | Training run creates experiment entries                     | Experiment list screenshot |
| UAT-07 | Researcher | Deploy best experiment            | Selected model changes to deployed status                   | API response + screenshot  |
| UAT-08 | Admin      | Approve pending user              | User status changes to approved                             | Admin table screenshot     |
| UAT-09 | Admin      | Update user role to researcher    | Role update persists after refresh                          | Screenshot                 |
| UAT-10 | User       | Open sentiment/news view          | News and sentiment cards load without error                 | Screenshot                 |
| UAT-11 | User       | Trigger alert check endpoint      | Triggered alerts return with reason and context             | API response               |
| UAT-12 | User       | Logout                            | Session invalidated and protected pages blocked             | Screenshot                 |

## Acceptance Criteria

- All 12 scenarios pass without high-severity defects.
- Any medium defect must have mitigation or rollback plan.
- Product owner signs off on evidence package.

## Execution Template

- Build version:
- Environment URL:
- Tester:
- Date:
- Result summary: PASS / FAIL
- Defects raised:
