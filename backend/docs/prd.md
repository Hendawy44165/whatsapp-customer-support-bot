# Customer Support Bot PRD

## 1. Overview
This bot helps the user with their online journey on the Nuit Fragrances brand from answering their queries to doing complex tasks like handling their CRM and tracking their shipping and recommending products based on their preferences and past purchases.

## 2. QA Agent PRD
### What it does
* Brand Voice 
* Answer Inquires related to policies and FAQ
* Ask further info when needed for complex tasks for the ReAct agent later
* For complex tasks, it tries to recommend ideas, then redirects to human if failed
* It tries to find a simple solution if the direct answer is a no like how a real customer support agent cares about customer satisfaction
* It breaks down the needed tasks based on what the ReAct agent can handle
* It can speak in English and Arabic with the Egyptian dialect or the MSA
### What it doesn't do
* Answer unrelated questions
* Answers very frustrated users on its own
* Respond in any language outside the specified ones.

## 3. ReAct Agent PRD
### What it does
* Asks the QA agent for further info if needed
* Update the CRM
* Fetch data from the CRM
* Track the Order
* Recommend products based on the CRM history and similar users purchases and given conditions if found
### What it doesn't do
* Pay on the behalf of the user

## 4. Router Agent PRD
### What it does
* Detects current user sentiment
* Redirects the initial message to the human escalator agent, or the QA agent with the right needed info
* Block unrelated quesions
### What it doesn't do
* Answer questions
* Handle anything outside the routing
* Handles the route between the QA and ReAct agent.

## 5. Human Escalation Agent PRD
### What it does
* Generate the urgency score
* Generate the conv summary
* Recommend some actions
* Call a tool to add the message to the internal queue
### What it doesn't do
* Notify the human agent manually

