import tensorflow as tf
import argparse
import utils

# import wandb

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

parser = argparse.ArgumentParser()
parser.add_argument('--nets', type=str, required=True)
parser.add_argument('--batch_size', type=int, default=32)
parser.add_argument('--lr', type=float, default=0.001)
parser.add_argument('--epochs', type=int, default=100)
args = parser.parse_args()

print(args)
# wandb.init(project="conv-nets", name=args.nets.lower())

model = utils.choose_nets(args.nets)

cifar100 = tf.keras.datasets.cifar10


from dataset_helper import read_stock_image
x_train, y_train, x_test, y_test = read_stock_image(image_width=64,image_height=64)

x_train  = x_train / 255.0
x_test =  x_test / 255.0

print("x_train, y_train, x_test, y_test:",x_train.shape, y_train.shape, x_test.shape, y_test.shape)
train_ds = tf.data.Dataset.from_tensor_slices(
    (x_train, y_train)).shuffle(100).batch(args.batch_size)
test_ds = tf.data.Dataset.from_tensor_slices(
    (x_test, y_test)).batch(args.batch_size)

loss_object = tf.keras.losses.CategoricalCrossentropy()
optimizer = tf.keras.optimizers.Adam(args.lr)

train_loss = tf.keras.metrics.Mean(name='train_loss')
train_accuracy = tf.keras.metrics.Accuracy(
    name='train_accuracy')

test_loss = tf.keras.metrics.Mean(name='test_loss')
test_accuracy = tf.keras.metrics.Accuracy(
    name='test_accuracy')

print(train_ds)
# @tf.function
def train_step(images, labels):
    with tf.GradientTape() as tape:
        predictions = model(images, training=True)
        # predictions = tf.cast(tf.argmax(predictions,axis=-1),tf.float32)
        print("predictions",predictions)
        print("labels",labels)
        loss = loss_object(labels, predictions)
    gradients = tape.gradient(loss, model.trainable_variables)
    optimizer.apply_gradients(zip(gradients, model.trainable_variables))
    print(loss)
    train_loss(loss)
    predictions = tf.round(predictions)
    print("train_accuracy predictions:",predictions)
    train_accuracy(labels, predictions)


# @tf.function
def test_step(images, labels):
    predictions = model(images)
    t_loss = loss_object(labels, predictions)

    test_loss(t_loss)
    predictions = tf.round(predictions)
    print("test_accuracy predictions:",predictions)
    test_accuracy(labels, predictions)


for epoch in range(args.epochs):
    for images, labels in train_ds:
        train_step(images, labels)

    template = 'Epoch: [{}/{}], Loss: {}, Accuracy: {}'
    print(template.format(epoch+1,
                          args.epochs,
                          train_loss.result(),
                          train_accuracy.result()*100))


    # for test_images, test_labels in test_ds:
    #     test_step(test_images, test_labels)

    # template = 'Epoch: [{}/{}], Loss: {}, Accuracy: {}, Test Loss: {}, Test Accuracy: {}'
    # print(template.format(epoch+1,
    #                       args.epochs,
    #                       train_loss.result(),
    #                       train_accuracy.result()*100,
    #                       test_loss.result(),
    #                       test_accuracy.result()*100))

    # wandb.log({
    #     "TrainLoss": train_loss.result(),
    #     "TestLoss": test_loss.result(),
    #     "TrainAcc": train_accuracy.result()*100,
    #     "TestAcc": test_accuracy.result()*100
    # })
    train_loss.reset_states()
    test_loss.reset_states()
    train_accuracy.reset_states()
    test_accuracy.reset_states()

for test_images, test_labels in test_ds:
    test_step(test_images, test_labels)

template = 'Test Loss: {}, Test Accuracy: {}'
print(template.format(test_loss.result(),
                      test_accuracy.result()*100))