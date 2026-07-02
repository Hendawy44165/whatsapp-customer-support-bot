# What makes a good vs bad RAG output?
## Good
* Gets the related data if found. If not found, outputs it will redirect to a human.
* Gets the data that is only related to the user question.
* Sometimes RAG output is not related, it doesn't use it then.
## Bad
* Always try to answer even if data not found
* In multi purpose, misses some key information the user wanted to know implicitly or explicitly.
* Hallucinates data
* Uses old unrelated conv history
* Misses key info from old conv history
