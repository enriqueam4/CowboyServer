import torch

try:
    device = torch.cuda.get_device_name(0)
    print('Available GPU:', str(device))
except RuntimeError:
    print('Please make sure you selected GPU as a hardware accelerator in Runtime --> Change runtime type')

import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import h5py
import cv2
import matplotlib.pyplot as plt
from tkinter import *
from tkinter import filedialog


def main():
    root = Tk()
    root.withdraw()
    hf_file = filedialog.askopenfilename(title="Select h5 data file")
    if hf_file == "":
        return

    filepath = filedialog.askopenfilename(title="Select weight file")
    if filepath == "":
        return
    print("yeehoo")
    checkpoint = torch.load(filepath, map_location='cpu')
    print("weehoo")
    # Initiate a model
    model = atomsegnet()
    # Load weights into the model
    model.load_state_dict(checkpoint)
    gen = generate_batches(hf_file, batch_size=10)
    test_imgs, gt = next(gen.batch(10, mode='val'))
    gen.close_()
    prediction = model.forward(test_imgs)
    prediction = prediction.data.numpy()
    k = 4
    fig = plt.figure(figsize=(12, 12))
    ax1 = fig.add_subplot(131)
    ax1.imshow(test_imgs[k, 0, :, :], cmap='gray')
    ax1.set_title('Training image')
    ax2 = fig.add_subplot(132)
    ax2.imshow(gt[k, 0, :, :], cmap='RdBu_r', interpolation='Gaussian')
    ax2.set_title('Ground truth')
    ax3 = fig.add_subplot(133)
    ax3.imshow(prediction[k, 0, :, :], cmap='RdBu_r', interpolation='Gaussian')
    ax3.set_title('Model prediction')
    plt.show()



class conv2dblock(nn.Module):
    def __init__(self, input_channels, output_channels,
                 kernel_size=3, stride=1, padding=1,
                 use_batchnorm=False, lrelu_a=0.01,
                 dropout_=0):
        """Creates a block consisting of convolutional
        layer, leaky relu and (optionally) dropout and
        batch normalization
        Args:
            input_channels: number of channels in the previous/input layer
            output_channels: number of the output channels for the present layer
            kernel_size: size (in pixels) of convolutional filter
            stride: value of convolutional filter stride
            padding: value of padding at the edges
            use_batchnorm (boolean): usage of batch normalization
            lrelu_a: value of alpha parameter in leaky/paramteric ReLU activation
            dropout_: value of dropout
        """
        super(conv2dblock, self).__init__()
        block = []
        block.append(nn.Conv2d(input_channels,
                               output_channels,
                               kernel_size=kernel_size,
                               stride=stride,
                               padding=padding))
        if dropout_ > 0:
            block.append(nn.Dropout(dropout_))
        block.append(nn.LeakyReLU(negative_slope=lrelu_a))
        if use_batchnorm:
            block.append(nn.BatchNorm2d(output_channels))
        self.block = nn.Sequential(*block)

    def forward(self, x):
        """Forward path"""
        output = self.block(x)
        return output


class dilation_block(nn.Module):

    def __init__(self, input_channels, output_channels,
                 dilation_values, padding_values,
                 kernel_size=3, stride=1, lrelu_a=0.01,
                 use_batchnorm=False, dropout_=0):
        """Creates a block with dilated convolutional
           layers (aka atrous convolutions)
        Args:
            input_channels: number of channels in the previous/input layer
            output_channels: number of the output channels for the present layer
            dilation_values: list of dilation rates for convolution operation
            kernel_size: size (in pixels) of convolutional filter
            stride: value of convolutional filter stride
            padding: value of padding at the edges
            use_batchnorm (boolean): usage of batch normalization
            lrelu_a: value of alpha parameter in leaky/paramteric ReLU activation
            dropout_: value of dropout
        """
        super(dilation_block, self).__init__()
        atrous_module = []
        for idx, (dil, pad) in enumerate(zip(dilation_values, padding_values)):
            input_channels = output_channels if idx > 0 else input_channels
            atrous_module.append(nn.Conv2d(input_channels,
                                           output_channels,
                                           kernel_size=kernel_size,
                                           stride=stride,
                                           padding=pad,
                                           dilation=dil,
                                           bias=True))
            if dropout_ > 0:
                atrous_module.append(nn.Dropout(dropout_))
            atrous_module.append(nn.LeakyReLU(negative_slope=lrelu_a))
            if use_batchnorm:
                atrous_module.append(nn.BatchNorm2d(output_channels))
        self.atrous_module = nn.Sequential(*atrous_module)

    def forward(self, x):
        """Forward path"""
        atrous_layers = []
        for conv_layer in self.atrous_module:
            x = conv_layer(x)
            atrous_layers.append(x.unsqueeze(-1))
        return torch.sum(torch.cat(atrous_layers, dim=-1), dim=-1)


class upsample_block(nn.Module):

    def __init__(self, input_channels, output_channels,
                 mode='interpolate', kernel_size=1,
                 stride=1, padding=0):
        """Defines upsampling block performed either with
           bilinear interpolation followed by 1-by-1
           convolution or with a transposed convolution
        Args:
            input_channels: number of channels in the previous/input layer
            output_channels: number of the output channels for the present layer
            mode: upsampling mode (default: 'interpolate')
            kernel_size: size (in pixels) of convolutional filter
            stride: value of convolutional filter stride
            padding: value of padding at the edges
        """
        super(upsample_block, self).__init__()
        self.mode = mode
        self.conv = nn.Conv2d(
            input_channels, output_channels,
            kernel_size=kernel_size,
            stride=stride, padding=padding)
        self.conv_t = nn.ConvTranspose2d(
            input_channels, output_channels,
            kernel_size=2, stride=2, padding=0)

    def forward(self, x):
        """Defines a forward path"""
        if self.mode == 'interpolate':
            x = F.interpolate(
                x, scale_factor=2,
                mode='bilinear', align_corners=False)
            return self.conv(x)
        return self.conv_t(x)


class atomsegnet(nn.Module):
    def __init__(self, nb_filters=32):
        '''Builds  a fully convolutional neural network model
        Args:
            nb_filters: number of filters in the first convolutional layer
        '''
        super(atomsegnet, self).__init__()
        self.c1 = conv2dblock(1, nb_filters)

        self.c2 = nn.Sequential(conv2dblock(nb_filters,
                                            nb_filters * 2),
                                conv2dblock(nb_filters * 2,
                                            nb_filters * 2))

        self.c3 = nn.Sequential(conv2dblock(nb_filters * 2,
                                            nb_filters * 4,
                                            dropout_=0.3),
                                conv2dblock(nb_filters * 4,
                                            nb_filters * 4,
                                            dropout_=0.3))

        self.bn = dilation_block(nb_filters * 4,
                                 nb_filters * 8,
                                 dilation_values=[2, 4, 6],
                                 padding_values=[2, 4, 6],
                                 dropout_=0.5)

        self.upsample_block1 = upsample_block(nb_filters * 8,
                                              nb_filters * 4)

        self.c4 = nn.Sequential(conv2dblock(nb_filters * 8,
                                            nb_filters * 4,
                                            dropout_=0.3),
                                conv2dblock(nb_filters * 4,
                                            nb_filters * 4,
                                            dropout_=0.3))

        self.upsample_block2 = upsample_block(nb_filters * 4,
                                              nb_filters * 2)

        self.c5 = nn.Sequential(conv2dblock(nb_filters * 4,
                                            nb_filters * 2),
                                conv2dblock(nb_filters * 2,
                                            nb_filters * 2))

        self.upsample_block3 = upsample_block(nb_filters * 2,
                                              nb_filters)

        self.c6 = conv2dblock(nb_filters * 2,
                              nb_filters)

        self.px = nn.Conv2d(nb_filters,
                            1,
                            kernel_size=1,
                            stride=1,
                            padding=0)

    def forward(self, x):
        """Defines a forward path"""
        # Contracting path
        c1 = self.c1(x)
        d1 = F.max_pool2d(c1, kernel_size=2, stride=2)
        c2 = self.c2(d1)
        d2 = F.max_pool2d(c2, kernel_size=2, stride=2)
        c3 = self.c3(d2)
        d3 = F.max_pool2d(c3, kernel_size=2, stride=2)
        bn = self.bn(d3)
        u3 = self.upsample_block1(bn)
        u3 = torch.cat([c3, u3], dim=1)
        u3 = self.c4(u3)
        u2 = self.upsample_block2(u3)
        u2 = torch.cat([c2, u2], dim=1)
        u2 = self.c5(u2)
        u1 = self.upsample_block3(u2)
        u1 = torch.cat([c1, u1], dim=1)
        u1 = self.c6(u1)
        px = self.px(u1)
        output = torch.sigmoid(px)
        return output


class generate_batches:
    def __init__(self, hf_file, batch_size, *args):
        """Creates a batch generator.
        Args:
            hf_file: path to hdf5 file with training data
            batch_size: size of generated batch
            args: (tuple): image resizing during training (min_size, max_size, step)
        """
        self.f = h5py.File(hf_file, 'r')
        self.batch_size = batch_size
        try:
            self.resize_ = args[0]
        except IndexError:
            self.resize_ = None

    def steps(self, mode='training'):
        """Estimates number of steps per epoch"""
        if mode == 'val':
            n_samples = self.f['X_test'][:].shape[0]
        else:
            n_samples = self.f['X_train'][:].shape[0]
        return np.arange(n_samples // self.batch_size)

    def batch(self, idx, mode='training'):
        """Generates batch of the selected size
        for training images and the corresponding
        ground truth"""

        def batch_resize(X_batch, y_batch, rs):
            """Resize all images in one batch"""

            if X_batch.shape[2:4] == (rs, rs):
                return X_batch, y_batch
            X_batch_r = np.zeros((X_batch.shape[0], X_batch.shape[1], rs, rs))
            y_batch_r = np.zeros((y_batch.shape[0], y_batch.shape[1], rs, rs))
            for i, (img, gt) in enumerate(zip(X_batch, y_batch)):
                img = cv2.resize(img[0], (rs, rs), cv2.INTER_CUBIC)
                img = np.expand_dims(img, axis=0)
                gt = cv2.resize(gt[0], (rs, rs))
                gt = np.expand_dims(gt, axis=0)
                X_batch_r[i, :, :, :] = img
                y_batch_r[i, :, :, :] = gt
            return X_batch_r, y_batch_r

        if mode == 'val':
            X_batch = self.f['X_test'][int(idx * self.batch_size):int((idx + 1) * self.batch_size)]
            y_batch = self.f['y_test'][int(idx * self.batch_size):int((idx + 1) * self.batch_size)]
        else:
            X_batch = self.f['X_train'][int(idx * self.batch_size):int((idx + 1) * self.batch_size)]
            y_batch = self.f['y_train'][int(idx * self.batch_size):int((idx + 1) * self.batch_size)]
        if self.resize_ != None:
            rs_arr = np.arange(self.resize_[0], self.resize_[1], self.resize_[2])
            rs = np.random.choice(rs_arr)
            X_batch, y_batch = batch_resize(X_batch, y_batch, rs)
        X_batch = torch.from_numpy(X_batch).float()
        y_batch = torch.from_numpy(y_batch).float()
        yield X_batch, y_batch

    def close_(self):
        """Closes h5 file"""
        if self.f:
            self.f.close()
            self.f = None


if __name__ == '__main__':
    main()

