# Frontend Route Map

## Route inventory

| Route         | Surface              | Notes                                |
| ------------- | -------------------- | ------------------------------------ |
| `/`           | HTML login surface   | Renders the application landing page |
| `/login`      | HTML login page      | Primary anonymous entry page         |
| `/dashboard`  | HTML dashboard       | Authenticated landing page           |
| `/upload`     | HTML upload page     | EEG upload workflow page             |
| `/analysis`   | HTML analysis page   | Workflow/progress page               |
| `/prediction` | HTML prediction page | Model output and uncertainty summary |
| `/reports`    | HTML reports page    | Report center                        |
| `/health`     | API probe            | Existing service health endpoint     |
| `/livez`      | liveness probe       | Operational liveness signal          |
| `/readyz`     | readiness probe      | MP-1/MP-3 readiness signal           |

## Wiring note

The HTML routes are attached on the same production app object that `uvicorn` serves. This is the route surface that was missing in the prior regression.

## Verification target

The deployed path must keep these pages reachable after startup and recovery.
