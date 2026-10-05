from learning_harness import LearningSession, Store, DemoModel

store = Store(':memory:')
session = LearningSession.create(store, 'Understand routing', [
    'A router selects experts and weights their outputs.'
])
block = session.state['document']['blocks'][0]
annotation = session.annotate(block['id'], 2, 8, 'router', 'How can this learn?')
session.step(DemoModel(), annotation['id'])
print(annotation['thread'][-1]['text'])
# The learner, not the model, decides when a question is resolved.
session.resolve(annotation['id'])
