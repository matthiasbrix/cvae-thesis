import numpy as np
import torch

# produces the z/y spaces for a single batch
def _get_batch_spaces(solver, x, y=None):
    y_space = None
    if solver.cvae_mode:
        x = x.view(-1, solver.data_loader.input_dim).to(solver.device)
        y = y.to(solver.device)
        _, _, _, z_space = solver.model(x, y)
    elif solver.tdcvae_mode:
        x_t, x_next = x
        x_t, x_next = x_t.view(-1, solver.data_loader.input_dim).to(solver.device),\
        x_next.view(-1, solver.data_loader.input_dim).to(solver.device)
        _, _, _, _, z_space, y_space = solver.model(x_t, x_next)
    else:
        x = x.view(-1, solver.data_loader.input_dim).to(solver.device)
        _, _, _, z_space = solver.model(x) # vae
    return y_space, z_space

# Used for retrieving the latent spaces available (z and y)
# transformation is only set when using rotation or scaling.
def get_latent_spaces(solver, transformation=None):
    z_space = np.zeros((solver.data_loader.num_test_samples, solver.model.z_dim))
    y_space = np.zeros((solver.data_loader.num_test_samples, solver.model.z_dim))
    data_labels = np.zeros((solver.data_loader.num_test_samples))
    test_loader = solver.data_loader.get_new_test_data_loader()
    solver.model.eval()
    with torch.no_grad():
        for batch_idx, data in enumerate(test_loader):
            batch_start_idx = batch_idx*solver.data_loader.batch_size
            batch_end_idx = (batch_idx+1)*solver.data_loader.batch_size
            if solver.data_loader.with_labels:
                x, targets = data[0], data[1]
                if transformation is not None:
                    x = transformation.preprocess_batch(x, batch_start_idx, batch_end_idx)
                y_batch_space, z_batch_space = _get_batch_spaces(solver, x, targets)
            else:
                x = data
                if transformation is not None:
                    x = transformation.preprocess_batch(x, batch_start_idx, batch_end_idx)
                y_batch_space, z_batch_space = _get_batch_spaces(solver, x)
            data_labels[batch_start_idx:batch_end_idx] = targets
            z_space[batch_start_idx:batch_end_idx, :] = z_batch_space.cpu().numpy()
            if y_batch_space is not None:
                y_space[batch_start_idx:batch_end_idx, :] = y_batch_space.cpu().numpy()
    return z_space, y_space, data_labels

# transforming images to produce alphas/radiuses
def transform_images(solver, preprocessing, test_loader, ys):
    with torch.no_grad():
        data_labels = np.zeros((solver.data_loader.num_test_samples))
        for batch_idx, data in enumerate(test_loader):
            if solver.data_loader.with_labels:
                x_t, targets = data[0], data[1]
            else:
                x_t = data
            batch_start_idx = batch_idx*solver.data_loader.batch_size
            batch_end_idx = (batch_idx+1)*solver.data_loader.batch_size
            data_labels[batch_start_idx:batch_end_idx] = targets
            # do transformations for each scale and then over all thetas
            for i in range(ys.shape[0]):
                for j in range(ys.shape[1]):
                    scale = np.around(preprocessing.scales[i], decimals=2)
                    theta = preprocessing.thetas[j]
                    x_t_transformed = preprocessing.preprocess_batch(x_t, scale, theta)
                    y_batch_space, _ = _get_batch_spaces(solver, x_t_transformed)
                    ys[i, j, batch_start_idx:batch_end_idx, :] = y_batch_space.cpu().numpy()

