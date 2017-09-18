1. Данные для обучения/вывода
2. Скрипт для обучения
3. Скрипт для вывода
4. Небольшой рефакторинг


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
