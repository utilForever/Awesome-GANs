from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import tensorflow as tf
import numpy as np

import sys
import time

import ebgan_model as ebgan

sys.path.append('../')
import image_utils as iu
from datasets import MNISTDataSet as DataSet


results = {
    'output': './gen_img/',
    'model': './model/EBGAN-model.ckpt'
}

train_global_step = {
    'global_global_step': 200001,
    'logging_interval': 1000,
}


def main():
    start_time = time.time()  # Clocking start

    # MNIST Dataset load
    mnist = DataSet(ds_path="./").data

    # GPU configure
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True

    with tf.Session(config=config) as s:
        # EBGAN Model
        model = ebgan.EBGAN(s, enable_pull_away=True)  # using pull away loss # EBGAN-PT

        # Initializing
        s.run(tf.global_variables_initializer())

        d_overpowered = False
        for global_step in range(train_global_step['global_global_step']):
            batch_x, _ = mnist.train.next_batch(model.batch_size)  # with batch_size, 64
            batch_x = np.reshape(batch_x, [-1] + model.image_shape[1:])
            batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)  # 64 x 128

            # Update D network
            if not d_overpowered:
                _, d_loss = s.run([model.d_op, model.d_loss],
                                  feed_dict={
                                      model.x: batch_x,
                                      model.z: batch_z,
                                  })

            # Update G network
            _, g_loss = s.run([model.g_op, model.g_loss],
                              feed_dict={
                                  model.z: batch_z,
                              })

            d_overpowered = d_loss < g_loss / 2.

            # Logging
            if global_step % train_global_step['logging_interval'] == 0:
                batch_x, _ = mnist.test.next_batch(model.batch_size)
                batch_x = np.reshape(batch_x, [-1] + model.image_shape[1:])
                batch_z = np.random.uniform(-1., 1., [model.batch_size, model.z_dim]).astype(np.float32)

                d_loss, g_loss, summary = s.run([model.d_loss, model.g_loss, model.merged],
                                                feed_dict={
                                                    model.x: batch_x,
                                                    model.z: batch_z,
                                                })

                d_overpowered = d_loss < g_loss / 2.

                # Print loss
                print("[+] Step %08d => " % global_step,
                      " D loss : {:.8f}".format(d_loss),
                      " G loss : {:.8f}".format(g_loss))

                # Training G model with sample image and noise
                sample_z = np.random.uniform(-1., 1., [model.sample_num, model.z_dim]).astype(np.float32)
                samples = s.run(model.g,
                                feed_dict={
                                    model.z: sample_z,
                                })

                # Summary saver
                model.writer.add_summary(summary, global_global_step=global_step)

                # Export image generated by model G
                sample_image_height = model.sample_size
                sample_image_width = model.sample_size
                sample_dir = results['output'] + 'train_{:08d}.png'.format(global_step)

                # Generated image save
                iu.save_images(samples,
                               size=[sample_image_height, sample_image_width],
                               image_path=sample_dir)

                # Model save
                model.saver.save(s, results['model'], global_global_step=global_step)

    end_time = time.time() - start_time  # Clocking end

    # Elapsed time
    print("[+] Elapsed time {:.8f}s".format(end_time))

    # Close tf.Session
    s.close()


if __name__ == '__main__':
    main()
