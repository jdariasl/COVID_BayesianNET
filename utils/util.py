import torch
import os
import shutil
import time
from collections import OrderedDict
import json
import torch.optim as optim
import pandas as pd
from model.models import BDenseNet, DenseNet, BEfficientNet, EfficientNet
import csv
import numpy as np


def write_score(writer, iter, mode, metrics):
    writer.add_scalar(mode + '/loss', metrics.data['loss'], iter)
    writer.add_scalar(mode + '/acc', metrics.data['correct'] / metrics.data['total'], iter)


def write_train_val_score(writer, epoch, train_stats, val_stats):
    writer.add_scalars('Loss', {'train': train_stats[0],
                                'val': val_stats[0],
                                }, epoch)
    writer.add_scalars('Coeff', {'train': train_stats[1],
                                 'val': val_stats[1],
                                 }, epoch)

    writer.add_scalars('Air', {'train': train_stats[2],
                               'val': val_stats[2],
                               }, epoch)

    writer.add_scalars('CSF', {'train': train_stats[3],
                               'val': val_stats[3],
                               }, epoch)
    writer.add_scalars('GM', {'train': train_stats[4],
                              'val': val_stats[4],
                              }, epoch)
    writer.add_scalars('WM', {'train': train_stats[5],
                              'val': val_stats[5],
                              }, epoch)
    return


def showgradients(model):
    for param in model.parameters():
        print(type(param.data), param.size())
        print("GRADS= \n", param.grad)





def datestr():
    now = time.gmtime()
    return '{}{:02}{:02}_{:02}{:02}'.format(now.tm_year, now.tm_mon, now.tm_mday, now.tm_hour, now.tm_min)


def save_checkpoint(state, is_best, path,  filename='last'):

    name = os.path.join(path, filename+'_checkpoint.pth.tar')
    print(name)
    torch.save(state, name)



def save_model(model,optimizer, args, metrics, epoch, best_pred_loss,confusion_matrix):
    loss = metrics.data['bacc']
    save_path = args.save
    make_dirs(save_path)
    
    with open(save_path + '/training_arguments.txt', 'w') as f:
        json.dump(args.__dict__, f, indent=2)
    
    is_best = False
    #print(loss)
    #print(best_pred_loss)
    if loss > best_pred_loss:
        is_best = True
        best_pred_loss = loss
        save_checkpoint({'epoch': epoch,
                         'state_dict': model.state_dict(),
                         'optimizer': optimizer.state_dict(),
                         'metrics': metrics.data },
                        is_best, save_path, args.model + "_best")
        np.save(save_path + 'best_confusion_matrix.npy',confusion_matrix.cpu().numpy())
            
    else:
        save_checkpoint({'epoch': epoch,
                         'state_dict': model.state_dict(),
                         'optimizer': optimizer.state_dict(),
                         'metrics': metrics.data},
                        False, save_path, args.model + "_last")

    return best_pred_loss

def load_model(args):
    checkpoint = torch.load(args.saved_model)
    model,bflag = select_model(args)
    model.load_state_dict(checkpoint['state_dict'])

    if (args.cuda):
        model.cuda()

    optimizer = select_optimizer(args,model)
    optimizer.load_state_dict(checkpoint['optimizer'])
    epoch = checkpoint['epoch']
    return model, optimizer, epoch, bflag


def make_dirs(path):
    if not os.path.exists(path):

        os.makedirs(path)


def create_stats_files(path):
    train_f = open(os.path.join(path, 'train.csv'), 'w')
    val_f = open(os.path.join(path, 'val.csv'), 'w')
    return train_f, val_f


def read_json_file(fname):
    with open(fname, 'r') as handle:
        return json.load(handle, object_hook=OrderedDict)


def write_json_file(content, fname):
    with open(fname, 'w') as handle:
        json.dump(content, handle, indent=4, sort_keys=False)


def read_filepaths(file):
    paths, labels = [], []
    with open(file, 'r') as f:
        lines = f.read().splitlines()

        for idx, line in enumerate(lines):
            if ('/ c o' in line):
                break
            #print(line)    
            subjid, path, label = line.split(' ')

            paths.append(path)
            labels.append(label)
    labes_array = np.array(labels)
    classes = np.unique(labes_array)
    for i in classes:
        print('Clase={}-Samples={}'.format(i, np.sum(labes_array == i)))
    return paths, labels

def select_model(args):
    if args.model == 'BDenseNet':
        return BDenseNet(args.classes), True #Flag: True: Bayesian model, False: Frequentist model
    elif args.model == 'DenseNet':
        return DenseNet(args.classes), False
    elif args.model == 'EfficientNet':
        return EfficientNet(args.classes), False
    elif args.model == 'BEfficientNet':
        return BEfficientNet(args.classes), True



def select_optimizer(args, model):
    if args.opt == 'sgd':
        return optim.SGD(model.parameters(), lr=args.lr, momentum=0.5, weight_decay=args.weight_decay)
    elif args.opt == 'adam':
        return optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    elif args.opt == 'rmsprop':
        return optim.RMSprop(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)


def print_stats(args, epoch, num_samples, trainloader, metrics):
    if (num_samples % args.log_interval == 1):
        print("Epoch:{:2d}\tSample:{:5d}/{:5d}\tLoss:{:.4f}\tAccuracy:{:.2f}".format(epoch,
                                                                                         num_samples,
                                                                                         len(
                                                                                             trainloader) * args.batch_size,
                                                                                         metrics.data[
                                                                                             'loss'] / num_samples,
                                                                                         metrics.data[
                                                                                             'correct'] /
                                                                                         metrics.data[
                                                                                             'total']))


def print_summary(args, epoch, num_samples, metrics, mode=''):
    print(mode + "\n SUMMARY EPOCH:{:2d}\tSample:{:5d}/{:5d}\tLoss:{:.4f}\tAccuracy:{:.2f}\tBalancedAccuracy:{:.2f}\n".format(epoch,
                                                                                                     num_samples,
                                                                                                     num_samples ,
                                                                                                     metrics.data[
                                                                                                         'loss'] / num_samples,                                                                             
                                                                                                     metrics.data[
                                                                                                         'correct'] /
                                                                                                     metrics.data[
                                                                                                         'total'],
                                                                                                     metrics.data[
                                                                                                         'bacc']/num_samples))


def confusion_matrix(nb_classes):



    confusion_matrix = torch.zeros(nb_classes, nb_classes)
    with torch.no_grad():
        for i, (inputs, classes) in enumerate(dataloaders['val']):
            inputs = inputs.to(device)
            classes = classes.to(device)
            outputs = model_ft(inputs)
            _, preds = torch.max(outputs, 1)
            for t, p in zip(classes.view(-1), preds.view(-1)):
                    confusion_matrix[t.long(), p.long()] += 1

    print(confusion_matrix)

class Metrics:
    def __init__(self, path, keys=None, writer=None):
        self.writer = writer

        self.data = {'correct': 0,
                     'total': 0,
                     'loss': 0,
                     'accuracy': 0,
                     'bacc':0,
                     }
        self.save_path = path

    def reset(self):
        for key in self.data:
            self.data[key] = 0

    def update_key(self, key, value, n=1):
        if self.writer is not None:
            self.writer.add_scalar(key, value)
        self.data[key] += value

    def update(self, values):
        for key in self.data:
            self.data[key] += values[key]
    
    def replace(self, values):
        for key in values:
            self.data[key] = values[key]

    def avg_acc(self):
        return self.data['correct'] / self.data['total']

    def avg_loss(self):
        return self.data['loss'] / self.data['total']

    def save(self):
        with open(self.save_path, 'w') as save_file:
            a = 0  # csv.writer()
            # TODO
