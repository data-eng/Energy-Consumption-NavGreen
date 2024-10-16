import logging
import torch.nn as nn

logger = logging.getLogger(__name__)
logger.setLevel(logging.CRITICAL)
formatter = logging.Formatter('%(asctime)s:%(lineno)d:%(levelname)s:%(name)s:%(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)


class Transformer(nn.Module):
    def __init__(self, in_size=16, sequence_len=1, out_size=1, nhead=1, num_layers=1, dim_feedforward=2048, dropout=0):
        super(Transformer, self).__init__()

        self.nhead = nhead
        self.enc_layer = nn.TransformerEncoderLayer(d_model=in_size, nhead=nhead, dim_feedforward=dim_feedforward, dropout=dropout)
        self.encoder = nn.TransformerEncoder(self.enc_layer, num_layers=num_layers)
        self.dec_layer = nn.TransformerDecoderLayer(d_model=in_size, nhead=nhead, dim_feedforward=dim_feedforward, dropout=dropout)
        self.decoder = nn.TransformerDecoder(self.dec_layer, num_layers=num_layers)
        self.regressor = nn.Linear(in_size*sequence_len, out_size)
        self.init_weights()

    def init_weights(self):
        """
        Initializes the weights and biases of the classifier linear layer:

        - Sets the bias of the classifier linear layer to zero.
        - Initializes the weights with values drawn from a Xavier uniform distribution.
        """ 
        self.regressor.bias.data.zero_()
        nn.init.xavier_uniform_(self.regressor.weight.data)
        
    def forward(self, x, mask=None):
        """
        Forward pass of the transformer model:

        - Passes the encoded input through the transformer encoder layer.
        - Passes the output of the encoder through the decoder linear layer.

        :param x: input tensor
        :param mask: optional mask tensor for missing values
        :return: output tensor after passing through the transformer model
        """
        x = x.permute(1, 0, 2)

        if mask is not None:
            x = self.encoder(src=x, src_key_padding_mask=mask)
            x = self.decoder(tgt=x, memory=x, tgt_key_padding_mask=mask, memory_key_padding_mask=mask)
        else:
            x = self.encoder(src=x)
            x = self.decoder(tgt=x, memory=x)

        x = x.permute(1, 0, 2).reshape(x.shape[1], -1)
        x = self.regressor(input=x)

        return x