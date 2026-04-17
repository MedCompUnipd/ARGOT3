#!/usr/bin/python3

import tensorflow as tf
from tensorflow.keras import layers, metrics, regularizers
from tensorflow import keras
import os


def get_saved_model(model_path):
    model = keras.models.load_model(model_path)

    model_path, model_folder = os.path.split(model_path)
    if not model_folder:
        model_path, model_folder = os.path.split(model_path)

    ont, fold, epoch = model_folder.split('_')

    return model, int(fold), int(epoch)


def focal_loss(gamma=1.0, alpha=0.75):
    def loss(y_true, y_pred):
        # Ensure floats
        y_true = tf.cast(y_true, tf.float32)
        y_pred = tf.clip_by_value(y_pred, 1e-7, 1. - 1e-7)

        # Compute focal loss
        cross_entropy = - (y_true * tf.math.log(y_pred) + (1. - y_true) * tf.math.log(1. - y_pred))
        focal_weight = alpha * tf.pow(1. - y_pred, gamma) * y_true + (1. - alpha) * tf.pow(y_pred, gamma) * (1. - y_true)
        loss = focal_weight * cross_entropy

        return tf.reduce_mean(loss)

    return loss


def residual_block(x, filters, kernel_size, strides):
    shortcut = x
    x = layers.Conv1D(filters, kernel_size=kernel_size, strides=strides, padding='same')(x)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Dropout(0.25)(x)
    x = layers.Conv1D(filters, kernel_size=kernel_size, strides=strides, padding='same')(x)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Dropout(0.25)(x)
    x = layers.Add()([x, shortcut])

    return x


def recursive_block(x, recursize):
    shortcut = x
    x = layers.Bidirectional(layers.LSTM(recursize, return_sequences=True))(x)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Dropout(0.25)(x)
    x = layers.Bidirectional(layers.LSTM(recursize, return_sequences=True))(x)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Dropout(0.25)(x)
    x = layers.Add()([x, shortcut])

    return x


def get_model_cco(out_channels):
    input = layers.Input(shape=(None, 1280))
    mask = layers.Lambda(lambda x: tf.reduce_any(tf.not_equal(x, 0.0), axis=-1))(input)

    x = layers.Conv1D(256, kernel_size=7, strides=1, padding='same')(input)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Dropout(0.25)(x)
    x = residual_block(x, 256, kernel_size=5, strides=1)
    x = residual_block(x, 256, kernel_size=5, strides=1)

    # Manually apply mask to outputs
    mask = layers.Lambda(lambda x: tf.cast(tf.expand_dims(x, axis=-1), tf.float32))(mask)
    x = x * mask  # Zero out padded time steps

    x = layers.Bidirectional(layers.LSTM(128, return_sequences=True))(x)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = recursive_block(x, 128)
    x = recursive_block(x, 128)

    # GlobalAveragePooling — also apply masked average
    x_masked = layers.Multiply()([x, mask])
    x_sum = layers.Lambda(lambda x: tf.reduce_sum(x, axis=1))(x_masked)
    lengths = layers.Lambda(lambda m: tf.reduce_sum(m, axis=1))(mask)
    x = layers.Lambda(lambda inputs: inputs[0] / tf.maximum(inputs[1], 1.0))([x_sum, lengths])

    # === Optional: Intermediate Dense Layer + Dropout ===
    x = layers.Dense(512, activation='relu')(x)
    x = layers.Dropout(0.5)(x)

    output = layers.Dense(out_channels, activation='sigmoid')(x)

    model = tf.keras.Model(inputs=input, outputs=output)

    optimizer = tf.keras.optimizers.Adam(learning_rate=0.0005, clipnorm=1.0, weight_decay=1e-5)
    model.compile(loss=focal_loss(), optimizer=optimizer, metrics=[metrics.BinaryAccuracy()])

    return model


def get_model_mfo(out_channels):
    input = layers.Input(shape=(None, 1280))
    mask = layers.Lambda(lambda x: tf.reduce_any(tf.not_equal(x, 0.0), axis=-1))(input)

    x = layers.Conv1D(256, kernel_size=7, strides=1, padding='same')(input)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Dropout(0.25)(x)
    x = residual_block(x, 256, kernel_size=5, strides=1)
    x = residual_block(x, 256, kernel_size=5, strides=1)

    # Manually apply mask to outputs
    mask = layers.Lambda(lambda x: tf.cast(tf.expand_dims(x, axis=-1), tf.float32))(mask)
    x = x * mask  # Zero out padded time steps

    x = layers.Bidirectional(layers.LSTM(256, return_sequences=True))(x)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = recursive_block(x, 256)
    x = recursive_block(x, 256)

    # GlobalAveragePooling — also apply masked average
    x_masked = layers.Multiply()([x, mask])
    x_sum = layers.Lambda(lambda x: tf.reduce_sum(x, axis=1))(x_masked)
    lengths = layers.Lambda(lambda m: tf.reduce_sum(m, axis=1))(mask)
    x = layers.Lambda(lambda inputs: inputs[0] / tf.maximum(inputs[1], 1.0))([x_sum, lengths])

    # === Optional: Intermediate Dense Layer + Dropout ===
    x = layers.Dense(512, activation='relu')(x)
    x = layers.Dropout(0.5)(x)

    output = layers.Dense(out_channels, activation='sigmoid')(x)

    model = tf.keras.Model(inputs=input, outputs=output)

    optimizer = tf.keras.optimizers.Adam(learning_rate=0.0002, clipnorm=1.0, weight_decay=1e-5)
    model.compile(loss=focal_loss(), optimizer=optimizer, metrics=[metrics.BinaryAccuracy()])
    # model.compile(loss=custom_binary_crossentropy_mfo, optimizer=optimizer, metrics=[metrics.BinaryAccuracy()])

    return model


def get_model_bpo(out_channels):
    input = layers.Input(shape=(None, 1280))
    mask = layers.Lambda(lambda x: tf.reduce_any(tf.not_equal(x, 0.0), axis=-1))(input)

    x = layers.Conv1D(512, kernel_size=7, strides=1, padding='same')(input)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Dropout(0.25)(x)
    x = residual_block(x, 512, kernel_size=5, strides=1)
    x = residual_block(x, 512, kernel_size=5, strides=1)

    # Manually apply mask to outputs
    mask_exp = layers.Lambda(lambda x: tf.cast(tf.expand_dims(x, axis=-1), tf.float32))(mask)
    x = x * mask_exp  # Zero out padded time steps

    x = layers.Bidirectional(layers.LSTM(512, return_sequences=True))(x)
    x = layers.LayerNormalization()(x)
    x = layers.ReLU()(x)
    x = recursive_block(x, 512)
    x = recursive_block(x, 512)

    # GlobalAveragePooling — also apply masked average
    x_masked = layers.Multiply()([x, mask_exp])
    x_sum = layers.Lambda(lambda x: tf.reduce_sum(x, axis=1))(x_masked)
    lengths = layers.Lambda(lambda m: tf.reduce_sum(m, axis=1))(mask_exp)
    x = layers.Lambda(lambda inputs: inputs[0] / tf.maximum(inputs[1], 1.0))([x_sum, lengths])

    # === Optional: Intermediate Dense Layer + Dropout ===
    x = layers.Dense(1024, activation='relu')(x)
    x = layers.Dropout(0.5)(x)

    output = layers.Dense(out_channels, activation='sigmoid')(x)

    model = tf.keras.Model(inputs=input, outputs=output)

    optimizer = tf.keras.optimizers.Adam(learning_rate=0.0002, clipnorm=1.0, weight_decay=1e-5)
    model.compile(loss=focal_loss(), optimizer=optimizer, metrics=[metrics.BinaryAccuracy()])

    return model
