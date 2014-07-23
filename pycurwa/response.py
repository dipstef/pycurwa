from codecs import getincrementaldecoder, lookup, BOM_UTF8


def decode_response(rep, header_string):
    encoding = 'utf8'  # default encoding

    header = header_string.splitlines()
    for line in header:
        line = line.lower().replace(' ', '')
        if not line.startswith('content-type:') or ('text' not in line and 'application' not in line):
            continue

        none, delimiter, charset = line.rpartition('charset=')
        if delimiter:
            charset = charset.split(';')
            if charset:
                encoding = charset[0]

    # self.log.debug('Decoded %s' % encoding )
    if lookup(encoding).name == 'utf-8' and rep.startswith(BOM_UTF8):
        encoding = 'utf-8-sig'

    decoder = getincrementaldecoder(encoding)('replace')
    rep = decoder.decode(rep, True)

    # TODO: html_un-escape as default

    return rep