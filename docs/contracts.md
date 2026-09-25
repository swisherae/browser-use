# Operation Contracts

One contract per SSD. Every class and attribute named here appears in `docs/domain-model.md`.

```text
Operation: createTask(instructions: Text, primaryModel: AIModel, backupModel: AIModel)
Cross-references: Use case Look Up Information Online
Preconditions:
  - A Developer exists
  - An AIModel exists to act as the primary model, reached through a ProviderAccount
    whose apiKey is set
Postconditions:
  - A Task instance was created
  - Task.instructions was set to instructions
  - Task.status was set to notStarted
  - Task.answerFormat was set to plain text
  - The Task was associated with the Developer
  - The Task was associated with the primaryModel AIModel as primary model
  - The Task was associated with the backupModel AIModel as backup model
```

```text
Operation: runTask(stepLimit: Number)
Cross-references: Use case Submit Web Form
Preconditions:
  - A Task exists with Task.status notStarted, associated with a Developer and with an
    AIModel as primary model
  - Every Secret named by a placeholder in Task.instructions exists and is associated
    with that Developer
Postconditions:
  - Task.stepLimit was set to stepLimit
  - Task.status was set to finished
  - Step instances were created
  - Each Step was associated with the Task
  - Step.number was set to its position in the run
  - Step.evaluation was set to the model's judgement of the previous step
  - Step.nextGoal was set to the model's stated goal for that step
  - A PageSnapshot instance was created for each Step
  - Each PageSnapshot was associated with its Step
  - Each PageSnapshot was associated with the WebPage it was taken from
  - A Screenshot instance was created and associated with each PageSnapshot
  - PageElement instances were created and associated with their PageSnapshot
  - Action instances were created and associated with their Step
  - Action.kind was set to input for each field filled, and to click for the option
    choices and the Submit button
  - Action.textEntered was set to the value typed for each input Action
  - Action.result was set to the outcome reported for that Action
  - Each input Action was associated with the PageElement it targeted
  - Each input Action that typed a secret was associated with that Secret
  - An Answer instance was created
  - Answer.text was set to the response the Website returned
  - Answer.succeeded was set to true
  - The Answer was associated with the Task
```

```text
Operation: setSiteRule(pattern: Text, kind: Text)
Cross-references: Use case Collect Data From Website
Preconditions:
  - A Developer exists
  - No SiteRule with this pattern and kind is already associated with that Developer
Postconditions:
  - A SiteRule instance was created
  - SiteRule.pattern was set to pattern
  - SiteRule.kind was set to kind, either allowed or prohibited
  - The SiteRule was associated with the Developer
  - The SiteRule was associated with each Website whose domain matches pattern
```
