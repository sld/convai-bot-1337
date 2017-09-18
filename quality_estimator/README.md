1. Данные для обучения/вывода

- data_preparation.py - скрипт для предобработки данных
  Вход: json от convai: [dialogs]
    [
      {
        evaluation: [u1 (userId, quality), u2 (userId, quality)],
        users: [u1 (id, userType), u2 (id, userType)],
        thread: [text (text, userId, evaluation)]
      }
    ]

  -- main(with_oversampling). Выход: [X, X_test, y, y_test]
     Есть вариант с oversampling'ом.

    ```
      X:

      [
        [  # D1
          [
            [5392], [2] # S1
          ],
          [
            [8132, 2601, 9974, 7521], [0, 0, 0, 0] # S2
          ]
        ],
        [...] # D2
      ]

      y: [label1, label2]
    ```

  -- main_sent(). Выход: [X, X_test, y, y_test]

    ```
      X shape: (5978, 3, 50)
      y shape: (5978,)
    ```


2. Скрипт для обучения

  - train_model.py
  После каждой эпохи сохраняет лучшую модель в data/models/dialog/model.pytorch

  - train_model_sent.py
  После каждой эпохи сохраняет лучшую модель в data/models/sentence/model.pytorch


  Dialog model quality:

  Test loss: 1.5103090259354786
  Test F1: 0.663385858327232
               precision    recall  f1-score   support

            0       0.79      0.82      0.81       240
            1       0.25      0.30      0.28        46
            2       0.37      0.23      0.28        44

  avg / total       0.66      0.67      0.66       330


  Utterance model quality:

Test F1: 0.6329217526193655
             precision    recall  f1-score   support

          1       0.68      0.73      0.70       623
          2       0.56      0.50      0.53       432

avg / total       0.63      0.64      0.63      1055




3. Скрипт для вывода - это server.py.
См. tests/test_server.py, чтобы понять как им пользоваться.
